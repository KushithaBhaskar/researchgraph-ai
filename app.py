"""ResearchGraph AI — Evidence-Linked Research Discovery (Streamlit + Neo4j)."""
from __future__ import annotations

import streamlit as st

from graph_db import ConfigError, DatabaseUnavailable, GraphDB, get_setting, load_config
from seed_data import EXAMPLE_QUESTIONS, seed_database

st.set_page_config(page_title="ResearchGraph AI", page_icon="🕸️", layout="wide")

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.8rem; max-width: 1250px;}
    .rg-hero {background: linear-gradient(120deg,#312e81,#4f46e5 60%,#0ea5e9);
              padding: 1.4rem 1.6rem; border-radius: 14px; color: white; margin-bottom: 1rem;}
    .rg-hero h1 {margin: 0; font-size: 1.9rem; color: white;}
    .rg-hero p {margin: .3rem 0 0; opacity: .92;}
    .rg-tag {display:inline-block; padding: 2px 10px; margin: 2px 4px 2px 0; border-radius: 999px;
             font-size: .8rem; background:#eef2ff; color:#3730a3; border:1px solid #c7d2fe;}
    .rg-tag.method {background:#ecfeff; color:#155e75; border-color:#a5f3fc;}
    .rg-tag.lim {background:#fff7ed; color:#9a3412; border-color:#fed7aa;}
    @media (max-width: 700px){ .rg-hero h1 {font-size: 1.4rem;} }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------- #
# Database connection
# --------------------------------------------------------------------------- #
@st.cache_resource(show_spinner=False)
def get_db() -> GraphDB:
    db = GraphDB(**load_config())
    db.verify()
    return db


def connect():
    """Return (db, error_message)."""
    try:
        return get_db(), None
    except ConfigError as exc:
        return None, str(exc)
    except DatabaseUnavailable as exc:
        return None, str(exc)


# --------------------------------------------------------------------------- #
# Answer generation
# --------------------------------------------------------------------------- #
def fallback_answer(result: dict) -> str:
    papers = result["papers"]
    lines = [
        f"Neo4j returned **{len(papers)} supporting paper(s)** for keywords "
        f"`{', '.join(result['keywords'])}`. Everything below comes from graph records.",
        "",
        "**Approaches and their recorded limitations**",
    ]
    for p in papers:
        methods = ", ".join(m["name"] for m in p["methods"]) or "no method recorded"
        lines.append(f"- **{p['title']}** ({p['year']}): approach: *{methods}*.")
        for lim in p["limitations"]:
            lines.append(f"  - Limitation (curator note): {lim['description']}")
    if result["related"]:
        lines += ["", "**Related papers found by graph traversal**"]
        for r in result["related"][:4]:
            why = []
            if r["shared"]:
                why.append("shares " + ", ".join(r["shared"][:3]))
            for e in r["explicit"][:1]:
                why.append(f"RELATED_TO from *{e['from']}*: {e['reason']}")
            lines.append(f"- **{r['paper']['title']}** ({r['paper']['year']}): " + "; ".join(why))
    return "\n".join(lines)


def evidence_text(result: dict) -> str:
    chunks = []
    for p in result["papers"]:
        chunks.append(
            f"PAPER: {p['title']} ({p['year']}) {p['url']}\n"
            f"Summary: {p['abstract']}\n"
            f"Concepts: {', '.join(c['name'] for c in p['concepts'])}\n"
            f"Methods: {', '.join(m['name'] for m in p['methods'])}\n"
            f"Limitations: {' | '.join(l['description'] for l in p['limitations'])}"
        )
    for r in result["related"][:4]:
        chunks.append(
            f"RELATED: {r['paper']['title']} ({r['paper']['year']}) shared={r['shared']} "
            f"explicit={[e['reason'] for e in r['explicit']]}"
        )
    return "\n\n".join(chunks)


def llm_answer(question: str, result: dict) -> str | None:
    key = get_setting("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=key)
        msg = client.messages.create(
            model=get_setting("LLM_MODEL", "claude-sonnet-4-5"),
            max_tokens=800,
            system=(
                "You answer research questions using ONLY the evidence provided from a "
                "Neo4j knowledge graph. Cite paper titles in bold. Never add papers, "
                "authors or findings that are not in the evidence. Limitations are "
                "curator notes; say so. Be concise (under 250 words)."
            ),
            messages=[{
                "role": "user",
                "content": f"Question: {question}\n\nEVIDENCE:\n{evidence_text(result)}",
            }],
        )
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    except Exception as exc:  # fall back deterministically
        st.session_state["llm_error"] = str(exc)
        return None


# --------------------------------------------------------------------------- #
# Graph visual
# --------------------------------------------------------------------------- #
COLORS = {
    "Paper": "#4f46e5", "Author": "#64748b", "Concept": "#0ea5e9",
    "Method": "#14b8a6", "Limitation": "#f97316", "ResearchSource": "#a855f7",
}


def build_dot(edges: list[dict], show_authors: bool) -> str:
    ids: dict[tuple, str] = {}
    lines = [
        "digraph G {", "rankdir=LR;", "bgcolor=transparent;",
        'node [style=filled, fontname="Helvetica", fontsize=10, fontcolor=white, shape=box];',
        'edge [fontname="Helvetica", fontsize=8, color="#94a3b8"];',
    ]

    def node(label: str, key: str, text: str) -> str:
        k = (label, key)
        if k not in ids:
            ids[k] = f"n{len(ids)}"
            t = (text or "")[:42].replace('"', "'")
            if len(text or "") > 42:
                t += "…"
            lines.append(f'{ids[k]} [label="{t}", fillcolor="{COLORS.get(label, "#334155")}"];')
        return ids[k]

    for e in edges:
        if e["rel"] == "AUTHORED_BY" and not show_authors:
            continue
        a = node("Paper", e["pid"], e["ptitle"])
        b = node(e["nlabel"], str(e["nkey"]), e["ntext"])
        lines.append(f'{a} -> {b} [label="{e["rel"]}"];')
    lines.append("}")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Sidebar: connection status + admin
# --------------------------------------------------------------------------- #
db, db_error = connect()
paper_count = 0

with st.sidebar:
    st.header("Database status")
    if db_error:
        st.error("Neo4j not connected")
        st.caption(db_error)
    else:
        stats = db.stats()
        paper_count = stats["nodes"].get("Paper", 0)
        st.success("Connected to Neo4j")
        st.caption(db.uri)
        st.write("**Nodes**", stats["nodes"] or "none yet")
        st.write("**Relationships**", stats["relationships"] or "none yet")
        if st.button("Initialize / re-seed database"):
            with st.spinner("Creating constraints and merging seed data…"):
                summary = seed_database(db)
            st.success(f"Seeded: {summary}")
            st.rerun()
    if st.button("Retry connection"):
        st.cache_resource.clear()
        st.rerun()
    st.divider()
    st.caption(
        "LLM: " + ("enabled (ANTHROPIC_API_KEY found)" if get_setting("ANTHROPIC_API_KEY")
                   else "off — deterministic evidence-grounded answers")
    )

# --------------------------------------------------------------------------- #
# Main page
# --------------------------------------------------------------------------- #
st.markdown(
    """
    <div class="rg-hero">
      <h1>🕸️ ResearchGraph AI</h1>
      <p>Evidence-linked research discovery: a Neo4j knowledge graph connects papers, concepts,
      methods, limitations, authors and sources to answer multi-hop research questions.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if db_error:
    st.error(
        "The app needs a live Neo4j database. Set NEO4J_URI, NEO4J_USERNAME and "
        "NEO4J_PASSWORD (in `.env` locally, or Streamlit secrets in the cloud), then press "
        "**Retry connection** in the sidebar."
    )
    st.stop()

if paper_count == 0:
    st.warning("The graph is empty. Click **Initialize / re-seed database** in the sidebar.")

st.session_state.setdefault("question", EXAMPLE_QUESTIONS[0])


def pick_example(q: str) -> None:
    st.session_state["question"] = q
    st.session_state["run"] = True


st.markdown("**Example questions**")
cols = st.columns(len(EXAMPLE_QUESTIONS))
for i, q in enumerate(EXAMPLE_QUESTIONS):
    cols[i].button(q if len(q) < 75 else q[:72] + "…", key=f"ex{i}",
                   on_click=pick_example, args=(q,), use_container_width=True)

with st.form("ask"):
    st.text_area("Research question", key="question", height=80)
    submitted = st.form_submit_button("🔎 Search the graph", type="primary")
if submitted:
    st.session_state["run"] = True

if st.session_state.pop("run", False):
    q = st.session_state["question"].strip()
    if q:
        st.session_state.pop("llm_error", None)
        with st.spinner("Running Cypher traversals against Neo4j…"):
            try:
                res = db.search(q)
            except DatabaseUnavailable as exc:
                st.error(str(exc))
                res = None
        if res is not None:
            res["answer"] = (llm_answer(q, res) if res["papers"] else None)
            res["answer_mode"] = "LLM (grounded in retrieved evidence)" if res["answer"] else "Deterministic (no LLM)"
            if not res["answer"] and res["papers"]:
                res["answer"] = fallback_answer(res)
            st.session_state["result"] = res

res = st.session_state.get("result")
if res:
    st.divider()
    if not res["papers"]:
        st.warning(
            "**No supporting evidence found in the graph** for this question "
            f"(keywords tried: {', '.join(res['keywords']) or 'none'}). "
            "No answer is generated because nothing in the database supports one."
        )
        with st.expander("Cypher executed"):
            for t in res["trace"]:
                st.code(t["cypher"], language="cypher")
        st.stop()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Papers matched", len(res["papers"]))
    m2.metric("Concepts found", len({c["name"] for p in res["papers"] for c in p["concepts"]}))
    m3.metric("Methods found", len({m["name"] for p in res["papers"] for m in p["methods"]}))
    m4.metric("Related papers (graph hops)", len(res["related"]))

    t_answer, t_papers, t_graph, t_evidence = st.tabs(
        ["💡 Answer", "📄 Papers, concepts & limitations", "🕸️ Graph explorer", "🔍 Sources & Cypher"]
    )

    with t_answer:
        st.caption(f"Answer mode: {res['answer_mode']}")
        if st.session_state.get("llm_error"):
            st.info("LLM call failed, so the deterministic answer is shown instead.")
        st.markdown(res["answer"])
        st.info(
            "How the graph helped: papers were ranked using text **and** their linked "
            "concepts/methods/limitations; related work was then found by hopping "
            "Paper → Concept/Method ← Paper and via RELATED_TO edges."
        )

    with t_papers:
        for p in res["papers"]:
            with st.container(border=True):
                st.markdown(f"#### [{p['title']}]({p['url']}) · {p['year']}")
                st.caption("Authors: " + ", ".join(p["authors"]))
                st.markdown(f"*Excerpt (curator summary, not the official abstract):* {p['excerpt']}")
                tags = "".join(f'<span class="rg-tag">{c["name"]}</span>' for c in p["concepts"])
                tags += "".join(f'<span class="rg-tag method">{m["name"]}</span>' for m in p["methods"])
                st.markdown(tags, unsafe_allow_html=True)
                for lim in p["limitations"]:
                    st.markdown(
                        f'<span class="rg-tag lim">Limitation</span> {lim["description"]} '
                        f'<em>({lim["basis"]})</em>',
                        unsafe_allow_html=True,
                    )
                st.caption(f"Graph relevance score: {p['score']}")
        st.subheader("Related approaches discovered through the graph")
        if not res["related"]:
            st.write("No additional related papers found.")
        for r in res["related"]:
            with st.container(border=True):
                st.markdown(f"**[{r['paper']['title']}]({r['paper']['url']})** · {r['paper']['year']}")
                if r["shared"]:
                    st.write("Shared concepts/methods: " + ", ".join(r["shared"]))
                if r["via_papers"]:
                    st.caption("Reached via: " + "; ".join(r["via_papers"]))
                for e in r["explicit"]:
                    st.write(f"RELATED_TO (from *{e['from']}*): {e['reason']}")
                    st.caption(f"Basis: {e['basis']}")

    with t_graph:
        show_auth = st.checkbox("Show authors", value=False)
        st.graphviz_chart(build_dot(res["edges"], show_auth), use_container_width=True)
        st.caption(
            "Legend — " + " · ".join(f"{k}" for k in COLORS)
            + ". Edges are real relationships returned by Neo4j."
        )

    with t_evidence:
        st.subheader("Sources")
        seen = set()
        for p in res["papers"]:
            for s in p["sources"]:
                if s["url"] not in seen:
                    seen.add(s["url"])
                    st.markdown(f"- [{s['title']}]({s['url']})")
        st.caption(
            "Titles, years and URLs are real arXiv listings. Concepts, methods, limitations and "
            "RELATED_TO links are curator-assigned and not verified by the paper authors."
        )
        st.subheader("Cypher executed for this answer")
        for t in res["trace"]:
            with st.expander(f"{t['step']} — {t['rows']} row(s), {t['ms']} ms"):
                st.code(t["cypher"], language="cypher")
                st.json(t["params"])
