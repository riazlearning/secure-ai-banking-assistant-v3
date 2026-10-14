import os
import uuid

import httpx
import streamlit as st


FASTAPI_URL = os.getenv(
    "FASTAPI_URL",
    "http://localhost:8000",
)

CHAT_ENDPOINT = f"{FASTAPI_URL}/api/v1/chat"


st.set_page_config(
    page_title=" AI Banking Assistant V3.  ........",
    page_icon="🏦",
    layout="centered",
)

st.title("🏦  AI Banking Assistant V3")
st.caption(" by LangGraph and Groq")

st.info(
    "Educational demo only. Do not enter real account "
    "numbers, passwords, or personal banking information."
)


# ---------------------------------------
# Initialize frontend session state
# ---------------------------------------

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []


# ---------------------------------------
# Display conversation history
# ---------------------------------------

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# ---------------------------------------
# Backend API client
# ---------------------------------------


async def send_message(message: str) -> str:
    async with httpx.AsyncClient(timeout=40.0) as client:
        response = await client.post(
            CHAT_ENDPOINT,
            json={
                "message": message,
                "thread_id": st.session_state.thread_id,
            },
        )

        response.raise_for_status()

        data = response.json()

        return data["answer"]


# ---------------------------------------
# Chat input
# ---------------------------------------

if prompt := st.chat_input("Ask a banking question..."):
    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt,
        }
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                import asyncio

                answer = asyncio.run(send_message(prompt))

            except httpx.TimeoutException:
                answer = "The banking assistant timed out. Please try again."

            except httpx.HTTPStatusError:
                answer = "The banking service could not process your request."

            except httpx.RequestError:
                answer = "Unable to connect to the banking API."

            except (KeyError, ValueError):
                answer = "The banking API returned an unexpected response."

        st.markdown(answer)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
        }
    )


# ---------------------------------------
# Start new conversation
# ---------------------------------------

if st.sidebar.button("New Conversationsss"):
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.messages = []
    st.rerun()

st.sidebar.caption("Thread ID")
st.sidebar.code(st.session_state.thread_id, language=None)
