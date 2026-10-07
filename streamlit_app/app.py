import json
import os
import time
import uuid
from datetime import datetime
from pathlib import Path

import requests
import streamlit as st

from api.agents.domains import DOMAIN_LABELS

FASTAPI_URL = os.getenv("FASTAPI_URL", "http://localhost:8000")
USERS = ["Hsuan AD", "Hsuan US", "Hsuan DE", "Hsuan SA"]
SAMPLE_QUESTIONS = json.loads(
    (
        Path(__file__).resolve().parent.parent / "data" / "sample_questions.json"
    ).read_text()
)

st.set_page_config(page_title="Knowledge System", page_icon="💬")
st.title("Knowledge System Chat")

username = st.sidebar.selectbox("Login as", USERS)


@st.cache_data(ttl=30)
def get_access(user: str) -> dict:
    resp = requests.get(f"{FASTAPI_URL}/access", params={"username": user}, timeout=10)
    resp.raise_for_status()
    return resp.json()


try:
    access = get_access(username)
except requests.RequestException as exc:
    st.sidebar.error(f"couldn't reach API: {exc}")
    access = {"role": "?", "allowed_domains": []}

st.sidebar.markdown(f"**Role:** {access['role']}")
st.sidebar.markdown("**Access**")
for domain, label in DOMAIN_LABELS.items():
    mark = "✅" if domain in access["allowed_domains"] else "❌"
    st.sidebar.markdown(f"{mark} {label}")


if st.session_state.get("active_username") != username:
    st.session_state.active_username = username
    st.session_state.history = []
    st.session_state.activity = []
    st.session_state.chat_box = ""
    st.session_state.is_processing = False
    st.session_state.pending_question = None
    for key in [
        k
        for k in st.session_state
        if k.startswith(("fb_done_", "show_reason_", "reason_"))
    ]:
        del st.session_state[key]


if st.session_state.get("clear_box"):
    st.session_state.chat_box = ""
    st.session_state.clear_box = False

st.sidebar.markdown("**Sample questions**")
st.sidebar.caption("Click to load into the chat box, then press Send.")
for domain in access["allowed_domains"]:
    for q in SAMPLE_QUESTIONS.get(domain, []):
        if st.sidebar.button(
            q, key=f"{domain}-{q}", disabled=st.session_state.is_processing
        ):
            st.session_state.chat_box = q
            st.rerun()


def send_feedback(entry: dict, rating: str, reason: str | None = None) -> None:
    try:
        requests.post(
            f"{FASTAPI_URL}/feedback",
            json={
                "username": entry["username"],
                "question": entry["question"],
                "answer": entry["text"],
                "route": entry["route"],
                "rating": rating,
                "reason": reason,
            },
            timeout=10,
        )
    except requests.RequestException:
        pass


def render_feedback(entry: dict) -> None:
    key = entry["id"]
    done = st.session_state.get(f"fb_done_{key}")
    if done:
        st.caption(f"Feedback recorded: {done}")
        return

    col1, col2 = st.columns([1, 1])
    if col1.button("👍", key=f"up_{key}"):
        send_feedback(entry, "up")
        st.session_state[f"fb_done_{key}"] = "👍"
        st.rerun()
    if col2.button("👎", key=f"down_{key}"):
        st.session_state[f"show_reason_{key}"] = True

    if st.session_state.get(f"show_reason_{key}"):
        reason = st.text_input("What went wrong?", key=f"reason_{key}")
        if st.button("Submit", key=f"submit_{key}"):
            send_feedback(entry, "down", reason)
            st.session_state[f"fb_done_{key}"] = "👎"
            st.session_state.pop(f"show_reason_{key}", None)
            st.rerun()


chat_tab, activity_tab = st.tabs(["Chat", "Activity Log"])

with chat_tab:
    for entry in st.session_state.history:
        if entry["role"] == "user":
            with st.chat_message("user"):
                st.markdown(entry["text"])
        else:
            with st.chat_message("assistant"):
                timing = (
                    f", {entry['duration_s']:.1f}s"
                    if entry.get("duration_s") is not None
                    else ""
                )
                st.markdown(
                    f"_(routed to: {entry['route']}{timing})_\n\n{entry['text']}"
                )
                if entry.get("sql"):
                    with st.expander("SQL query"):
                        st.code(entry["sql"], language="sql")
                if entry.get("sources"):
                    st.caption("Sources: " + ", ".join(entry["sources"]))
                render_feedback(entry)

    if st.session_state.is_processing:
        question = st.session_state.pending_question
        with st.chat_message("assistant"):
            with st.spinner("🤖 Thinking..."):
                start = time.monotonic()
                try:
                    resp = requests.post(
                        f"{FASTAPI_URL}/chat",
                        json={"username": username, "message": question},
                        timeout=150,  # above github_agent's FETCH_TIMEOUT + LLM_TIMEOUT (30 + 100)
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    answer, route, reason = (
                        data["answer"],
                        data.get("route", "none"),
                        data.get("reason", ""),
                    )
                    sql, sources = data.get("sql"), data.get("sources", [])
                except requests.RequestException as exc:
                    answer, route, reason, sql, sources = (
                        f"Request failed: {exc}",
                        "none",
                        "",
                        None,
                        [],
                    )
                duration_s = time.monotonic() - start

        st.session_state.history.append(
            {
                "id": str(uuid.uuid4()),
                "role": "assistant",
                "text": answer,
                "route": route,
                "sql": sql,
                "sources": sources,
                "question": question,
                "username": username,
                "duration_s": duration_s,
            }
        )
        st.session_state.activity.append(
            {
                "time": datetime.now().strftime("%H:%M:%S"),
                "username": username,
                "question": question,
                "route": route,
                "reason": reason,
                "duration_s": duration_s,
            }
        )
        st.session_state.is_processing = False
        st.rerun()

    with st.form("chat_form", clear_on_submit=False):
        box_col, send_col = st.columns([5, 1])
        box_col.text_input(
            "Ask something...",
            key="chat_box",
            label_visibility="collapsed",
            disabled=st.session_state.is_processing,
        )
        submitted = send_col.form_submit_button(
            "Send", disabled=st.session_state.is_processing
        )

    if submitted and not st.session_state.is_processing:
        question = st.session_state.chat_box.strip()
        if question:
            st.session_state.history.append(
                {"id": str(uuid.uuid4()), "role": "user", "text": question}
            )
            st.session_state.is_processing = True
            st.session_state.pending_question = question
            st.session_state.clear_box = True
            st.rerun()

with activity_tab:
    st.subheader("Question routing activity")
    if not st.session_state.activity:
        st.caption("No questions asked yet this session.")
    for item in reversed(st.session_state.activity):
        label = DOMAIN_LABELS.get(item["route"], item["route"])
        timing = (
            f" ({item['duration_s']:.1f}s)"
            if item.get("duration_s") is not None
            else ""
        )
        st.markdown(
            f"**{item['time']}**{timing} -- *{item['username']}* asked “{item['question']}” "
            f"→ routed to **{label}** -- {item['reason'] or 'no reason recorded'}"
        )
