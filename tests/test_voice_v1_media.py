import pytest
import wave

from backend.voice_v1.contracts import AudioFrame
from backend.voice_v1.media.capture import CaptureFeatures, comfort_noise_allowed
from backend.voice_v1.media.endpointing import AdaptiveEndpoint, finalize_turn_candidate
from backend.voice_v1.media.frames import AudioFrameError, resample_frame, validate_frame
from backend.voice_v1.media.worker import ProviderAdaptersMissing, WorkerAdapters, require_worker_adapters
from backend.voice_v1.media.replay import inspect_wav, iter_wav_frames
from backend.voice_v1.turn_policy import SlotKind


def frame(*, rate=8000, data=b"\0\0" * 80, fmt="s16le", seq=2, ts=123456) -> AudioFrame:
    return AudioFrame(data, rate, 1, fmt, "pcm", ts, seq)


def test_validates_frame_metadata_and_preserves_original():
    original = frame()
    assert validate_frame(original) is original
    with pytest.raises(AudioFrameError):
        validate_frame(frame(rate=0))
    with pytest.raises(AudioFrameError):
        validate_frame(frame(data=b""))
    with pytest.raises(AudioFrameError):
        validate_frame(frame(seq=-1))


def test_resampler_must_actually_return_target_rate_and_preserve_timestamp():
    class HonestFake:
        def resample(self, source, *, target_sample_rate_hz):
            return AudioFrame(b"\0\0" * 160, target_sample_rate_hz, 1, "s16le", "pcm", source.capture_monotonic_ns, source.sequence)

    out = resample_frame(frame(), target_sample_rate_hz=16000, adapter=HonestFake())
    assert out.sample_rate_hz == 16000
    assert out.capture_monotonic_ns == 123456

    class WrongTimestamp:
        def resample(self, source, *, target_sample_rate_hz):
            return AudioFrame(b"\0\0" * 160, target_sample_rate_hz, 1, "s16le", "pcm", source.capture_monotonic_ns + 1, source.sequence)

    with pytest.raises(AudioFrameError, match="timestamp"):
        resample_frame(frame(), target_sample_rate_hz=16000, adapter=WrongTimestamp())
    # Actual sample conversion is not provable from metadata alone; adapter integration
    # requires signal-quality tests against real input and output samples.


def test_capture_features_default_off_and_noise_is_opt_in():
    flags = CaptureFeatures.from_env({})
    assert flags == CaptureFeatures()
    assert not comfort_noise_allowed(flags)
    enabled = CaptureFeatures.from_env({"NK_AUDIO_COMFORT_NOISE": "true", "NK_AUDIO_AGC": "1"})
    assert comfort_noise_allowed(enabled)
    assert enabled.enabled_processing_flags() == ("automatic_gain_control",)
    with pytest.raises(ValueError):
        CaptureFeatures.from_env({"NK_AUDIO_AGC": "maybe"})


def test_adaptive_endpoint_uses_slot_policy_and_decoded_pcm_cadence():
    endpoint = AdaptiveEndpoint(SlotKind.YES_NO)
    assert not endpoint.update(frame(), is_speech=False)
    assert not endpoint.update(frame(), is_speech=True)
    assert not endpoint.update(frame(), is_speech=False)  # 10 ms
    for _ in range(14):
        ended = endpoint.update(frame(), is_speech=False)
    assert ended  # 150 ms minimum for short yes/no slot
    with pytest.raises(ValueError, match="decoded"):
        AdaptiveEndpoint(SlotKind.YES_NO).update(frame(fmt="opus"), is_speech=False)


def test_worker_readiness_does_not_claim_missing_provider_adapters():
    assert not all(WorkerAdapters().readiness().values())
    with pytest.raises(ProviderAdaptersMissing, match="livekit_session.*asr.*tts"):
        require_worker_adapters(WorkerAdapters())


def test_headless_wav_replay_preserves_rate_and_monotonic_frame_metadata(tmp_path):
    path = tmp_path / "fixture-8khz.wav"
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(8000)
        wav.writeframes(b"\x01\x00" * 800)
    frames = list(iter_wav_frames(path, frame_ms=20, capture_start_monotonic_ns=10_000))
    assert len(frames) == 5
    assert all(frame.sample_rate_hz == 8000 for frame in frames)
    assert [frame.sequence for frame in frames] == list(range(5))
    assert frames[1].capture_monotonic_ns > frames[0].capture_monotonic_ns
    assert inspect_wav(path)["duration_ms"] == 100


def test_replay_rejects_non_pcm16_wav(tmp_path):
    path = tmp_path / "fixture-8bit.wav"
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(1)
        wav.setframerate(8000)
        wav.writeframes(b"\x80" * 80)
    with pytest.raises(ValueError, match="PCM16"):
        list(iter_wav_frames(path))


def test_semantic_completion_must_confirm_acoustic_endpoint_candidate():
    class FixtureDetector:
        def is_turn_complete(self, transcript, *, active_slot):
            return transcript.endswith("?") and active_slot == "yes_no"

    detector = FixtureDetector()
    assert not finalize_turn_candidate(acoustic_endpoint=False, transcript="சரி?", active_slot="yes_no", detector=detector)
    assert not finalize_turn_candidate(acoustic_endpoint=True, transcript="எங்க தெருவுல...", active_slot="address", detector=detector)
    assert finalize_turn_candidate(acoustic_endpoint=True, transcript="ஆம்?", active_slot="yes_no", detector=detector)
