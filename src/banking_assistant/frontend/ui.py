"""Shared Streamlit chat and human review interface."""

import os
import math
import uuid
from datetime import datetime
from time import time
from zoneinfo import ZoneInfo

import httpx
import streamlit as st

from banking_assistant.api.chat_schemas import ChatResponse

CHAT_ENDPOINT = f"{os.getenv('FASTAPI_URL', 'http://localhost:8000').rstrip('/')}/api/v1/chat"
OUTCOMES = {
    "approved": ("success", "Approved — review accepted. Transfers are fictional simulations."),
    "rejected": ("warning", "Rejected — this operation was not executed."),
    "expired": ("warning", "Expired — this operation was not executed. Start a new request if needed."),
    "cancelled": ("info", "Cancelled — this operation was not executed."),
    "invalid_response": ("error", "Invalid response — this operation was not executed."),
}


def request_api(method: str, path: str = "", payload: dict | None = None) -> ChatResponse:
    with httpx.Client(timeout=40.0) as client:
        response = client.request(method, f"{CHAT_ENDPOINT}{path}", json=payload)
        response.raise_for_status()
        result = ChatResponse.model_validate(response.json())
    if result.thread_id != st.session_state.thread_id:
        raise ValueError("Response belongs to a different conversation")
    if (result.status == "approval_required") != bool(result.pending_approvals):
        raise ValueError("Inconsistent review response")
    for approval in result.pending_approvals:
        if not math.isfinite(approval.expires_at):
            raise ValueError("Invalid approval deadline")
        try:
            datetime.fromtimestamp(approval.expires_at, ZoneInfo("Asia/Riyadh"))
        except (OverflowError, OSError) as exc:
            raise ValueError("Invalid approval deadline") from exc
    return result


def accept_response(result: ChatResponse) -> None:
    # Validate the full response before changing any pending review state.
    st.session_state.pending_approvals = [item.model_dump() for item in result.pending_approvals]
    message = {"role": "assistant", "content": result.answer,
               "tool_traces": [trace.model_dump() for trace in result.tool_traces],
               "outcomes": {key: value.value for key, value in result.review_outcomes.items()}}
    if not st.session_state.messages or st.session_state.messages[-1] != message:
        st.session_state.messages.append(message)
    st.session_state.review_uncertain = False
    st.session_state.ui_error = None


def show_error(exc: Exception, reviewing: bool = False) -> None:
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        if code == 422:
            text = "Invalid response. Your review is still pending; refresh its status before trying again."
        elif code == 409:
            text = "This approval is stale or already resolved. Refresh its status to see the current outcome."
        else:
            text = "The banking service could not process the request. Refresh status before resubmitting a review."
    elif isinstance(exc, httpx.TimeoutException):
        text = "The request timed out. Its outcome is unknown; refresh status before resubmitting."
    elif isinstance(exc, httpx.RequestError):
        text = "Unable to connect to the banking API. Check the connection and refresh status."
    else:
        text = "The API returned an invalid response. Refresh status before resubmitting a review."
    st.session_state.ui_error = text
    # Never automatically resend an approval after an ambiguous failure.
    st.session_state.review_uncertain = reviewing or st.session_state.review_uncertain


def refresh_status() -> None:
    try:
        accept_response(request_api("GET", f"/{st.session_state.thread_id}/approvals"))
        st.rerun()
    except (httpx.HTTPError, ValueError) as exc:
        show_error(exc, reviewing=True)


@st.fragment(run_every="2s")
def review_panel() -> None:
    pending = st.session_state.pending_approvals
    if not pending:
        return
    for approval in pending:
        with st.container(border=True):
            expired = time() >= approval["expires_at"]
            st.subheader("Transfer review" if approval["tool_name"] == "transfer_money" else "Operation review")
            st.warning("Fictional simulation only. No money will move.")
            args = approval["args"]
            if approval["tool_name"] == "transfer_money":
                st.write(f"Recipient: {args.get('recipient', '—')}")
                st.write(f"Amount: {args.get('amount', '—')} {args.get('currency', '')}")
            with st.expander("Exact operation details"):
                st.write(approval["tool_name"])
                st.json(args)
            deadline = datetime.fromtimestamp(approval["expires_at"], ZoneInfo("Asia/Riyadh"))
            st.caption(f"Expires {deadline:%Y-%m-%d %H:%M:%S} (Asia/Riyadh)")
            if expired:
                st.warning("Approval deadline reached. Approval is disabled; refresh status to resolve expiry.")
            else:
                st.caption(f"{max(0, int(approval['expires_at'] - time()))} seconds remaining")
            disabled = expired or st.session_state.review_uncertain
            cols = st.columns(3)
            decision = None
            for col, label, value in zip(cols, ["Approve", "Reject", "Cancel"], ["approve", "reject", "cancel"]):
                if col.button(label, key=f"{value}_{approval['approval_id']}", disabled=disabled):
                    decision = value
            if decision:
                try:
                    with st.spinner("Submitting review..."):
                        result = request_api("POST", "/approvals", {
                            "thread_id": st.session_state.thread_id,
                            "approval_id": approval["approval_id"], "decision": decision,
                        })
                    accept_response(result)
                    st.rerun()
                except (httpx.HTTPError, ValueError) as exc:
                    show_error(exc, reviewing=True)
                    st.rerun()
    st.caption("Chat text such as ‘I approve’ does not approve an operation.")


def main() -> None:
    st.set_page_config(page_title="Secure AI Banking Assistant V3", page_icon="🏦", layout="centered")
    for key, default in {
        "thread_id": str(uuid.uuid4()), "messages": [], "pending_approvals": [],
        "review_uncertain": False, "ui_error": None,
    }.items():
        if key not in st.session_state:
            st.session_state[key] = default
    st.title("🏦 Secure AI Banking Assistant V3")
    st.caption("Powered by LangGraph and Groq")
    st.info("Educational demo only. Do not enter real account numbers, passwords, or personal banking information.")

    if st.sidebar.button("New Conversation"):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state.pending_approvals = []
        st.session_state.review_uncertain = False
        st.session_state.ui_error = None
        st.rerun()
    st.sidebar.caption("Starting a new conversation does not approve pending operations.")
    st.sidebar.caption("Thread ID")
    st.sidebar.code(st.session_state.thread_id, language=None)
    if st.sidebar.button("Refresh review status"):
        refresh_status()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                with st.expander("Tool trace"):
                    traces = message.get("tool_traces", [])
                    if not traces:
                        st.caption("No tool calls recorded for this response.")
                    for trace in traces:
                        st.text(f"{trace['tool_name']}: {trace['status']}")
                        st.caption(f"Call ID: {trace['tool_call_id']}")
                        st.json(trace["args"])
            for index, outcome in enumerate(message.get("outcomes", {}).values(), 1):
                level, text = OUTCOMES[outcome]
                getattr(st, level)(f"Operation {index}: {text}")
    if st.session_state.ui_error:
        st.error(st.session_state.ui_error)
    review_panel()
    if prompt := st.chat_input("Ask a banking question...", disabled=bool(st.session_state.pending_approvals) or st.session_state.review_uncertain):
        st.session_state.messages.append({"role": "user", "content": prompt})
        try:
            with st.spinner("Thinking..."):
                accept_response(request_api("POST", payload={"message": prompt, "thread_id": st.session_state.thread_id}))
        except (httpx.HTTPError, ValueError) as exc:
            show_error(exc, reviewing=True)
        st.rerun()
