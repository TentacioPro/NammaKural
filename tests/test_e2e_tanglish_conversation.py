"""End-to-end Tanglish multi-turn conversation test covering greeting, ambiguity, correction, OTP, HITL, and GCC packet."""

from __future__ import annotations

import uuid

from backend import agent_workflow, state
from backend.portal_bridge import build_gcc_preview_packet
from backend.state import issue_mobile_otp, seal_verified_turn, verify_mobile_otp


def test_e2e_tanglish_conversation_flow(monkeypatch) -> None:
    monkeypatch.setattr(state, "_REQUEST_HISTORY", [])
    monkeypatch.setattr(agent_workflow, "log_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(agent_workflow, "chat_backends", lambda mode: iter([{"provider": "mock-llm", "active_model": "gemma-4-mock"}]))

    def fake_chat(backend, messages, **options):
        user_msg = messages[-1]["content"].lower()
        if "vanakkam" in user_msg:
            return {"content": "Vanakkam! Nalla irukken, ungal street-la enna help venum?"}
        if "anna nagar" in user_msg:
            return {"content": "Anna Nagar-la Tower Park pakkama, illa Anna Arch pakkama?"}
        if "tower park" in user_msg and "illa" not in user_msg:
            return {"content": "Seri, Tower Park (Ward 103) note pannitten. OTP verify panni Confirm sollunga."}
        return {"content": "Seri, Anna Arch (Ward 102) ku maathitten. OTP verify panni Confirm sollunga."}

    monkeypatch.setattr(agent_workflow, "chat_message", fake_chat)

    sid = f"e2e-{uuid.uuid4().hex[:8]}"
    turns = [
        "Vanakkam! Epdi irukinga, enna help pannuvinga?",
        "Anna Nagar-la streetlight eriyala, romba irutta irukku",
        "Tower Park back side, Fifth Avenue pakkam",
        "Illa illa, Tower Park illa, Anna Arch pakkam",
    ]
    history: list[dict[str, str]] = []
    replies: list[str] = []
    last: dict = {}

    for u in turns:
        res = agent_workflow.run_workflow_turn(
            utterance=u,
            combined_text=u,
            state_code="tn",
            lang="tanglish",
            llm_mode="auto",
            history=history,
            session_id=sid,
            dpdp_consented=True,
        )
        assert res["display_text"]
        assert res["tts_text"] == res["display_text"]
        replies.append(res["display_text"])
        history.extend([{"role": "user", "text": u}, {"role": "agent", "text": res["display_text"]}])
        last = res

    assert len(set(replies)) == len(turns)
    assert last["fsm_state"] == "HITL_SEAL"
    assert last["analysis"]["landmark"]["ward"] == "Ward 102"
    assert last["complaint_version"] >= 2

    otp = issue_mobile_otp("+91 98XXXXXX10")
    ver = verify_mobile_otp(otp["otp_session_id"], otp["demo_otp_hint"])
    assert ver["verified"] is True

    lm = last["analysis"]["landmark"]
    s1 = seal_verified_turn(otp["otp_session_id"], "voice_double", "Confirm", False, lm["ward"], last["analysis"]["service_id"], last["analysis"]["urgency"]["tier"], str(last["complaint_version"]), turn_id="t1")
    assert s1.get("pending_confirmation") is True
    s2 = seal_verified_turn(otp["otp_session_id"], "voice_double", "உறுதி", False, lm["ward"], last["analysis"]["service_id"], last["analysis"]["urgency"]["tier"], str(last["complaint_version"]), turn_id="t2")
    assert s2["approved"] is True

    pkt = build_gcc_preview_packet(
        service_id=last["analysis"]["service_id"],
        landmark=lm,
        summary_text=" | ".join(turns),
        otp_verified=ver["verified"],
        hitl_approved=s2["approved"],
        complaint_version=last["complaint_version"],
    )
    assert pkt["ready_for_portal"] is True
    assert pkt["outbound_gov_requests"] is False
    assert pkt["fields"]["ward"] == "Ward 102"
