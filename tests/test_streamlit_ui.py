from pathlib import Path
from time import time
from unittest.mock import patch

import httpx
import pytest
from streamlit.testing.v1 import AppTest


def pending_response():
    return {
        "answer": "Review the operation.", "thread_id": "ui-thread",
        "status": "approval_required", "review_outcomes": {},
        "pending_approvals": [{"approval_id": "review-1", "tool_call_id": "call-1",
            "tool_name": "transfer_money", "args": {"recipient": "Demo", "amount": "20.00", "currency": "SAR"},
            "expires_at": time() + 300}],
    }


def app():
    ui = AppTest.from_file(Path(__file__).resolve().parents[1] / "frontend/app.py")
    ui.session_state["thread_id"] = "ui-thread"
    return ui


def response(data, status=200):
    return httpx.Response(status, json=data, request=httpx.Request("POST", "http://test"))


@pytest.mark.parametrize("decision,outcome", [("Approve", "approved"), ("Reject", "rejected"), ("Cancel", "cancelled"), ("Approve", "invalid_response")])
def test_review_actions_show_outcomes_and_restore_chat(decision, outcome):
    ui = app()
    with patch("httpx.Client.request", return_value=response(pending_response())):
        ui.run()
        ui.chat_input[0].set_value("Simulate transfer").run()
    assert not ui.exception
    assert ui.chat_input[0].disabled
    assert "Recipient: Demo" in [item.value for item in ui.markdown]
    completed = {"answer": "Review complete.", "thread_id": "ui-thread", "status": "completed",
                 "pending_approvals": [], "review_outcomes": {"fingerprint": outcome}}
    with patch("httpx.Client.request", return_value=response(completed)) as request:
        next(button for button in ui.button if button.label == decision).click().run()
    assert not ui.exception
    assert not ui.chat_input[0].disabled
    assert request.call_args.kwargs["json"]["decision"] == decision.lower()
    assert ui.session_state["messages"][-1]["outcomes"] == {"fingerprint": outcome}


def test_expired_approval_disabled_and_status_refresh_resolves_it():
    ui = app()
    pending = pending_response()
    pending["pending_approvals"][0]["expires_at"] = time() - 1
    ui.session_state["pending_approvals"] = pending["pending_approvals"]
    ui.run()
    assert next(button for button in ui.button if button.label == "Approve").disabled
    completed = {"answer": "Expired.", "thread_id": "ui-thread", "status": "completed",
                 "pending_approvals": [], "review_outcomes": {"fingerprint": "expired"}}
    with patch("httpx.Client.request", return_value=response(completed)) as request:
        next(button for button in ui.button if button.label == "Refresh review status").click().run()
    assert not ui.exception
    assert request.call_args.args[0] == "GET"
    assert not ui.chat_input[0].disabled
    assert any("Expired" in warning.value for warning in ui.warning)


@pytest.mark.parametrize("failure", ["timeout", "invalid", "422", "409"])
def test_ambiguous_or_invalid_response_keeps_review_and_requires_refresh(failure):
    ui = app()
    pending = pending_response()
    ui.session_state["pending_approvals"] = pending["pending_approvals"]
    ui.run()
    kwargs = ({"side_effect": httpx.ReadTimeout("timeout")} if failure == "timeout" else
              {"return_value": response({"bad": "payload"}, int(failure) if failure.isdigit() else 200)})
    with patch("httpx.Client.request", **kwargs):
        next(button for button in ui.button if button.label == "Approve").click().run()
    assert not ui.exception
    assert ui.session_state["pending_approvals"] == pending["pending_approvals"]
    assert ui.session_state["review_uncertain"]
    assert next(button for button in ui.button if button.label == "Approve").disabled
    assert ui.error
    with patch("httpx.Client.request", return_value=response(pending)):
        next(button for button in ui.button if button.label == "Refresh review status").click().run()
    assert not ui.session_state["review_uncertain"]
    assert not next(button for button in ui.button if button.label == "Approve").disabled


def test_package_entrypoint_loads_shared_ui():
    ui = AppTest.from_file(Path(__file__).resolve().parents[1] / "src/banking_assistant/frontend/app.py").run()
    assert not ui.exception
    assert ui.title[0].value == "🏦 Secure AI Banking Assistant V3"


def test_github_trace_is_visible_after_prompt():
    ui = app()
    completed = {
        "answer": "First three lines", "thread_id": "ui-thread",
        "tool_traces": [{"tool_call_id": "read-1", "tool_name": "get_file_contents",
                         "args": {"owner": "riazlearning", "repo": "secure-ai-banking-assistant-v3",
                                  "path": "README.md"}, "status": "success"}],
    }
    with patch("httpx.Client.request", return_value=response(completed)):
        ui.run()
        ui.chat_input[0].set_value("Fetch first 3 lines of README.md").run()
    assert not ui.exception
    assert any(item.value == "get_file_contents: success" for item in ui.text)
    assert ui.expander[0].label == "Tool trace"
