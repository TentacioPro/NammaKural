import asyncio

import pytest

from backend.voice_v1.contracts import AudioChunk, Reply, Transcript
from backend.voice_v1.observability import STAGE_SECONDS
from backend.voice_v1.session import VoiceSessionOrchestrator
from backend.voice_v1.turn_policy import SessionState


async def empty_frames():
    if False:
        yield None


class FakeASR:
    async def transcribe(self, frames, *, language, keyterms=()):
        yield Transcript("streetlight", is_final=False, language=language)
        yield Transcript("streetlight-a fix pannunga", is_final=True, language=language)


class FakeWorkflow:
    async def respond(self, transcript, *, session_id, turn_id):
        assert transcript == "streetlight-a fix pannunga"
        return Reply("சரி, பார்த்துக்கிறோம்.", "சரி, பார்த்துக்கிறோம்.", voice="ta-IN-test")


class FakeTTS:
    async def synthesize(self, text, *, language, voice, speaking_rate):
        assert text == "சரி, பார்த்துக்கிறோம்."
        assert language == "ta-IN"
        assert voice == "ta-IN-test"
        assert speaking_rate == 1.0
        yield AudioChunk(b"audio", "audio/pcm", 24000, 1, 0, 123)


def cancelled_workflow_count():
    for metric in STAGE_SECONDS.collect():
        for sample in metric.samples:
            if sample.name == "nk_voice_stage_duration_seconds_count" and sample.labels == {
                "stage": "workflow",
                "provider": "BlockingWorkflow",
                "outcome": "cancelled",
            }:
                return sample.value
    return 0


def test_session_orchestrator_streams_pipeline_and_returns_to_listening():
    async def scenario():
        agent = VoiceSessionOrchestrator(asr=FakeASR(), workflow=FakeWorkflow(), tts=FakeTTS())
        events = [event async for event in agent.stream_turn(
            session_id="session-1",
            turn_id="turn-1",
            frames=empty_frames(),
        )]

        assert [event.kind for event in events] == [
            "transcript_partial", "transcript_final", "reply", "audio"
        ]
        assert {event.session_id for event in events} == {"session-1"}
        assert {event.turn_id for event in events} == {"turn-1"}
        assert len({event.epoch for event in events}) == 1
        assert agent.coordinator("session-1").state is SessionState.LISTENING

    asyncio.run(scenario())


class BlockingWorkflow:
    def __init__(self):
        self.started = asyncio.Event()
        self.cancelled = asyncio.Event()

    async def respond(self, transcript, *, session_id, turn_id):
        self.started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.cancelled.set()
            raise


def test_committed_barge_in_cancels_provider_work_and_invalidates_epoch():
    async def scenario():
        workflow = BlockingWorkflow()
        agent = VoiceSessionOrchestrator(asr=FakeASR(), workflow=workflow, tts=FakeTTS())
        events = []
        cancelled_workflow_samples = cancelled_workflow_count()

        async def consume():
            async for event in agent.stream_turn(
                session_id="session-2",
                turn_id="turn-2",
                frames=empty_frames(),
            ):
                events.append(event)

        consumer = asyncio.create_task(consume())
        await asyncio.wait_for(workflow.started.wait(), timeout=1)
        old_epoch = agent.coordinator("session-2").epoch

        await agent.possible_barge_in("session-2")
        new_epoch = await agent.resolve_incoming_speech("session-2", is_backchannel=False)
        await asyncio.wait_for(consumer, timeout=1)

        assert new_epoch == old_epoch + 1
        assert workflow.cancelled.is_set()
        assert cancelled_workflow_count() == cancelled_workflow_samples + 1
        assert [event.kind for event in events].count("interrupted") == 1
        assert all(event.kind not in {"reply", "audio"} for event in events)
        assert agent.coordinator("session-2").state is SessionState.LISTENING

    asyncio.run(scenario())


class PausableTTS:
    def __init__(self):
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.cancelled = False

    async def synthesize(self, text, *, language, voice, speaking_rate):
        self.started.set()
        try:
            await self.release.wait()
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        yield AudioChunk(b"audio", "audio/pcm", 24000, 1, 0, 456)


def test_backchannel_resumes_without_cancelling_tts():
    async def scenario():
        tts = PausableTTS()
        agent = VoiceSessionOrchestrator(asr=FakeASR(), workflow=FakeWorkflow(), tts=tts)
        events = []

        async def consume():
            async for event in agent.stream_turn(
                session_id="session-3",
                turn_id="turn-3",
                frames=empty_frames(),
            ):
                events.append(event)

        consumer = asyncio.create_task(consume())
        await asyncio.wait_for(tts.started.wait(), timeout=1)
        await agent.possible_barge_in("session-3")
        await agent.resolve_incoming_speech("session-3", is_backchannel=True)
        tts.release.set()
        await asyncio.wait_for(consumer, timeout=1)

        assert not tts.cancelled
        assert any(event.kind == "audio" for event in events)
        assert agent.coordinator("session-3").state is SessionState.LISTENING

    asyncio.run(scenario())


def test_only_one_active_turn_per_session():
    async def scenario():
        workflow = BlockingWorkflow()
        agent = VoiceSessionOrchestrator(asr=FakeASR(), workflow=workflow, tts=FakeTTS())
        iterator = agent.stream_turn(session_id="session-4", turn_id="turn-4", frames=empty_frames())
        first = asyncio.create_task(iterator.__anext__())
        await asyncio.wait_for(workflow.started.wait(), timeout=1)
        with pytest.raises(RuntimeError, match="already has an active turn"):
            async for _ in agent.stream_turn(session_id="session-4", turn_id="turn-5", frames=empty_frames()):
                pass
        first.cancel()
        await asyncio.gather(first, return_exceptions=True)

    asyncio.run(scenario())
