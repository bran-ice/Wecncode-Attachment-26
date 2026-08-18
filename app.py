"""Streamlit chat over the Samsung manuals.

    streamlit run app.py

A thin view over `query.session.ChatSession` — the pipeline logic lives there
so it can be tested without driving a browser. What belongs here is only what
Streamlit itself owns: caching the expensive singletons across reruns, holding
the conversation in session state, and drawing.
"""

from __future__ import annotations

import streamlit as st

from core.config import ConfigError, load_settings
from core.logging_setup import setup_logging
from core.storage import Store, StoreError
from ingest.embed import build_embedder
from query.generate import build_generator, estimate_cost
from query.session import INGEST_COMMAND, ChatSession, check_store_ready

st.set_page_config(page_title="Samsung Manual RAG", page_icon="📱", layout="centered")

MODES = ["hybrid", "bm25", "dense"]
MODE_HELP = {
    "hybrid": "BM25 + vectors, fused. Best overall (Recall@5 0.93).",
    "bm25": "Keyword only. Strong on part numbers, weak on paraphrase.",
    "dense": "Vectors only. Strong on paraphrase, weak on exact strings.",
}


@st.cache_resource(show_spinner="Loading the index…")
def _load_settings():
    return load_settings()


@st.cache_resource(show_spinner="Opening the store…")
def _open_store(store_dir: str):
    # Cached across reruns, and every rerun is a new thread — see the
    # `multithread` note in core/storage.Store.
    return Store(store_dir, multithread=True)


@st.cache_resource(show_spinner="Loading the embedding model…")
def _load_embedder(_settings):
    return build_embedder(_settings)


@st.cache_resource
def _load_generator(_settings):
    return build_generator(_settings)


def _fatal(message: str, hint: str = "") -> None:
    """Stop with an instruction, never a traceback."""
    st.error(message)
    if hint:
        st.code(hint, language="powershell")
    st.stop()


def _bootstrap():
    setup_logging("WARNING")
    try:
        settings = _load_settings()
    except ConfigError as exc:
        _fatal(str(exc), "copy .env.example .env")

    if problem := check_store_ready(settings.store_dir):
        _fatal(*problem)

    try:
        store = _open_store(str(settings.store_dir))
    except StoreError as exc:
        _fatal(f"The index could not be opened: {exc}", INGEST_COMMAND)

    if problem := check_store_ready(settings.store_dir, store):
        _fatal(*problem)
    return settings, store


settings, store = _bootstrap()
documents = store.list_documents()

# --- sidebar --------------------------------------------------------------

with st.sidebar:
    st.subheader("Retrieval")
    mode = st.radio("Mode", MODES, index=0, help="\n\n".join(
        f"**{name}** — {text}" for name, text in MODE_HELP.items()
    ))
    st.caption(MODE_HELP[mode])

    model_names = sorted({doc.model for doc in documents})
    model_filter = st.selectbox("Limit to a model", ["All models", *model_names])
    top_k = st.slider("Passages per answer", 3, 10, 5)

    st.divider()
    st.caption(
        f"{len(documents)} manuals · {store.count_chunks():,} chunks · "
        f"{settings.gen_model}"
    )
    if st.button("Clear conversation", use_container_width=True):
        st.session_state.pop("session", None)
        st.rerun()

# --- session --------------------------------------------------------------

if "session" not in st.session_state:
    st.session_state.session = ChatSession(
        store=store,
        generator=_load_generator(settings),
        embedder=None,  # loaded on demand: BM25-only runs never need it
    )

session: ChatSession = st.session_state.session
session.mode = mode
session.top_k = top_k
session.model_filter = None if model_filter == "All models" else model_filter
if mode in ("hybrid", "dense") and session.embedder is None:
    session.embedder = _load_embedder(settings)

# --- history --------------------------------------------------------------

st.title("Samsung Manual RAG")
st.caption(
    "Answers come only from the indexed manuals, with a page citation for every "
    "claim. When the manuals don't cover it, it says so."
)


def _render_citations(answer) -> None:
    if not answer or not answer.citations:
        return
    st.caption("Sources")
    for citation in answer.citations:
        header = f"[{citation.marker}] {citation.label()}"
        if citation.section_path:
            header += f" — {citation.section_path}"
        with st.expander(header):
            st.write(citation.snippet)


def _render_readout(result) -> None:
    answer = result.answer
    if answer is None:
        return
    cost = estimate_cost(answer.input_tokens or 0, answer.output_tokens or 0)
    bits = [
        f"retrieval {result.retrieval_ms:.0f}ms",
        f"answer {answer.latency_ms:.0f}ms",
        f"{answer.input_tokens}in/{answer.output_tokens}out tokens",
        f"~${cost:.5f}",
    ]
    if result.collapsed:
        bits.append(f"{result.collapsed} duplicates collapsed")
    if result.expansion and result.expansion.rewritten:
        bits.append(f"searched as: “{result.expansion.rewritten}”")
    st.caption(" · ".join(bits))


for past in session.turns:
    with st.chat_message("user"):
        st.write(past.question)
    with st.chat_message("assistant"):
        if past.error:
            st.warning(past.error)
        else:
            st.markdown(past.answer.text if past.answer else "")
            _render_citations(past.answer)
            _render_readout(past)

# --- new turn -------------------------------------------------------------

if question := st.chat_input("Ask about your Samsung device…"):
    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        pieces: list[str] = []
        result = None
        for piece in session.ask(question):
            if isinstance(piece, str):
                pieces.append(piece)
                placeholder.markdown("".join(pieces) + "▌")
            else:
                result = piece

        if result is not None and result.error:
            placeholder.empty()
            st.warning(result.error)
        elif result is not None and result.answer is not None:
            # Re-render from the assembled answer: the refusal sentinel is
            # stripped there, and the streamed text still carries it.
            placeholder.markdown(result.answer.text)
            _render_citations(result.answer)
            _render_readout(result)
