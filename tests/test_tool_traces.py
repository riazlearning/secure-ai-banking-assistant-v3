import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from banking_assistant.services.chat_service import ChatService


@pytest.mark.parametrize("status", ["success", "error", "requested"])
def test_trace_uses_tool_result_and_excludes_previous_turn(status):
    call = {"id": "read-1", "name": "get_file_contents", "args": {
        "owner": "riazlearning", "repo": "secure-ai-banking-assistant-v3",
        "path": "README.md",
    }}
    messages = [
        HumanMessage(content="Old request"),
        AIMessage(content="", tool_calls=[{**call, "id": "old"}]),
        ToolMessage(content="old", tool_call_id="old"),
        HumanMessage(content="Fetch first 3 lines"),
        AIMessage(content="", tool_calls=[call]),
    ]
    if status != "requested":
        messages.append(ToolMessage(content="Do not expose raw tool output",
                                    tool_call_id="read-1", status=status))
    messages.append(AIMessage(content="Answer"))
    response = ChatService.response({"messages": messages}, "thread")
    assert len(response.tool_traces) == 1
    trace = response.tool_traces[0]
    assert trace.tool_name == "get_file_contents"
    assert trace.args == call["args"]
    assert trace.status == status
    assert "Do not expose" not in response.model_dump_json()


def test_answer_without_tool_calls_has_empty_trace():
    response = ChatService.response({"messages": [AIMessage(content="Hello")]}, "thread")
    assert response.tool_traces == []
