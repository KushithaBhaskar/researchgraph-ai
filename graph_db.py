"""Neo4j access layer for ResearchGraph AI.

All retrieval is done with real Cypher executed through the official Neo4j
Python driver. Every query that runs is recorded in a trace so the UI can show
judges exactly what the graph did.
"""
from __future__ import annotations

import os
import re
import time
from typing import Any

from neo4j import GraphDatabase
from neo4j.exceptions import AuthError, ConfigurationError, ServiceUnavailable

try:  # optional: load a local .env file during development
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass


class ConfigError(Exception):
    """Neo4j credentials are missing."""


class DatabaseUnavailable(Exception):
    """Neo4j could not be reached or rejected the credentials."""


LABELS = ["Paper", "Author", "Concept", "Method", "Limitation", "ResearchSource"]


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
def get_setting(name: str, default: str | None = None) -> str | None:
    """Read a setting from the environment, then Streamlit secrets."""
    value = os.getenv(name)
    if value:
        return value
    try:
        import streamlit as st

        secret = st.secrets.get(name)
        if secret:
            return str(secret)
    except Exception:
        pass
    return default


def load_config() -> dict[str, str]:
    cfg = {
        "uri": get_setting("NEO4J_URI"),
        "username": get_setting("NEO4J_USERNAME"),
        "password": get_setting("NEO4J_PASSWORD"),
    }
    missing = [
        env
        for env, key in (
            ("NEO4J_URI", "uri"),
            ("NEO4J_USERNAME", "username"),
            ("NEO4J_PASSWORD", "password"),
        )
        if not cfg[key]
    ]
    if missing:
        raise ConfigError(
            "Missing Neo4j configuration: "
            + ", ".join(missing)
            + ". Set them in .env (local) or Streamlit secrets (cloud)."
        )
    return cfg  # type: ignore[return-value]


# --------------------------------------------------------------------------- #
# Keyword extraction (deterministic, no LLM needed)
# --------------------------------------------------------------------------- #
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "by", "can", "do", "does",
    "for", "from", "has", "have", "how", "in", "into", "is", "it", "its", "of",
    "on", "or", "that", "the", "their", "them", "these", "this", "to", "was",
    "were", "what", "when", "where", "which", "while", "who", "why", "with",
    "approach", "approaches", "explored", "explore", "paper", "papers", "research",
    "researchers", "discuss", "discussed", "discusses", "alternative", "alternatives",
    "related", "limitations", "limitation", "about", "between", "using", "use",
    "used", "help", "helps", "address", "addresses", "ai", "llm", "llms",
    "limit", "limits", "work", "works", "show", "tell", "me", "some", "any",
}


def extract_keywords(question: str) -> list[str]:
    seen: list[str] = []
    for tok in re.findall(r"[a-z0-9]+", question.lower()):
        if len(tok) < 3 or tok in STOPWORDS:
            continue
        if len(tok) > 4 and tok.endswith("ies"):
            tok = tok[:-3] + "y"
        elif len(tok) > 4 and tok.endswith("s") and not tok.endswith("ss"):
            tok = tok[:-1]
        if tok not in seen:
            seen.append(tok)
    return seen


# --------------------------------------------------------------------------- #
# Cypher
# --------------------------------------------------------------------------- #
CONSTRAINTS = [
    "CREATE CONSTRAINT paper_id IF NOT EXISTS FOR (n:Paper) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT author_name IF NOT EXISTS FOR (n:Author) REQUIRE n.name IS UNIQUE",
    "CREATE CONSTRAINT concept_name IF NOT EXISTS FOR (n:Concept) REQUIRE n.name IS UNIQUE",
    "CREATE CONSTRAINT method_name IF NOT EXISTS FOR (n:Method) REQUIRE n.name IS UNIQUE",
    "CREATE CONSTRAINT limitation_id IF NOT EXISTS FOR (n:Limitation) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT source_url IF NOT EXISTS FOR (n:ResearchSource) REQUIRE n.url IS UNIQUE",
]

Q_MATCH_PAPERS = """
MATCH (p:Paper)
OPTIONAL MATCH (p)-[:COVERS]->(c:Concept)
OPTIONAL MATCH (p)-[:USES_METHOD]->(m:Method)
OPTIONAL MATCH (p)-[:HAS_LIMITATION]->(l:Limitation)
WITH p, collect(DISTINCT c) AS cs, collect(DISTINCT m) AS ms, collect(DISTINCT l) AS ls
WITH p, cs, ms, ls,
     reduce(s = 0, k IN $kw |
        s
        + CASE WHEN toLower(p.title) CONTAINS k THEN 3 ELSE 0 END
        + CASE WHEN toLower(p.abstract) CONTAINS k THEN 1 ELSE 0 END
        + 2 * size([c IN cs WHERE toLower(c.name) CONTAINS k OR toLower(c.description) CONTAINS k])
        + 2 * size([m IN ms WHERE toLower(m.name) CONTAINS k OR toLower(m.description) CONTAINS k])
        + size([l IN ls WHERE toLower(l.description) CONTAINS k])
     ) AS score
WHERE score > 0
RETURN p.id AS id, score
ORDER BY score DESC, p.year DESC
LIMIT $limit
"""

Q_PAPER_DETAILS = """
MATCH (p:Paper) WHERE p.id IN $ids
RETURN p {.id, .title, .year, .abstract, .source, .url} AS paper,
       [(p)-[:AUTHORED_BY]->(a:Author) | a.name] AS authors,
       [(p)-[:COVERS]->(c:Concept) | c {.name, .description}] AS concepts,
       [(p)-[:USES_METHOD]->(m:Method) | m {.name, .description}] AS methods,
       [(p)-[:HAS_LIMITATION]->(l:Limitation) | l {.description, .basis}] AS limitations,
       [(p)-[:SUPPORTED_BY]->(s:ResearchSource) | s {.title, .url}] AS sources
"""

Q_RELATED_SHARED = """
MATCH (p:Paper) WHERE p.id IN $ids
MATCH (p)-[:COVERS|USES_METHOD]->(shared)<-[:COVERS|USES_METHOD]-(r:Paper)
WHERE NOT r.id IN $ids
RETURN r {.id, .title, .year, .url} AS paper,
       collect(DISTINCT p.title) AS via_papers,
       collect(DISTINCT shared.name) AS shared,
       count(DISTINCT shared) AS n
ORDER BY n DESC
LIMIT 6
"""

Q_RELATED_EXPLICIT = """
MATCH (p:Paper)-[rel:RELATED_TO]-(r:Paper)
WHERE p.id IN $ids AND NOT r.id IN $ids
RETURN r {.id, .title, .year, .url} AS paper,
       p.title AS via_paper, rel.reason AS reason, rel.basis AS basis
"""

Q_EDGES = """
MATCH (p:Paper)-[r:AUTHORED_BY|COVERS|USES_METHOD|HAS_LIMITATION|SUPPORTED_BY|RELATED_TO]->(n)
WHERE p.id IN $ids
RETURN p.id AS pid, p.title AS ptitle, type(r) AS rel,
       labels(n)[0] AS nlabel,
       coalesce(n.id, n.name, n.url) AS nkey,
       coalesce(n.title, n.name, n.description) AS ntext
"""

Q_STATS_NODES = """
MATCH (n) WHERE any(l IN labels(n) WHERE l IN $labels)
RETURN labels(n)[0] AS label, count(*) AS n
"""

Q_STATS_RELS = "MATCH ()-[r]->() RETURN type(r) AS rel, count(*) AS n"


class GraphDB:
    def __init__(self, uri: str, username: str, password: str):
        self.uri = uri
        try:
            self.driver = GraphDatabase.driver(uri, auth=(username, password))
        except (ConfigurationError, ValueError) as exc:
            raise DatabaseUnavailable(f"Invalid NEO4J_URI '{uri}': {exc}") from exc

    # ---- connection ------------------------------------------------------- #
    def verify(self) -> None:
        try:
            self.driver.verify_connectivity()
        except AuthError as exc:
            raise DatabaseUnavailable(
                "Neo4j rejected the username/password (authentication failed)."
            ) from exc
        except (ServiceUnavailable, OSError) as exc:
            raise DatabaseUnavailable(
                f"Could not reach Neo4j at {self.uri}. Check the URI, that the "
                f"AuraDB instance is running (free instances pause when idle), "
                f"and your network. Details: {exc}"
            ) from exc
        except Exception as exc:  # any other driver error
            raise DatabaseUnavailable(f"Neo4j connection failed: {exc}") from exc

    def close(self) -> None:
        self.driver.close()

    # ---- query helper ----------------------------------------------------- #
    def run(self, query: str, **params: Any) -> list[dict[str, Any]]:
        try:
            with self.driver.session() as session:
                return session.run(query, params).data()
        except (ServiceUnavailable, AuthError, OSError) as exc:
            raise DatabaseUnavailable(f"Neo4j query failed: {exc}") from exc

    def _traced(self, trace: list, step: str, query: str, **params: Any) -> list[dict]:
        start = time.perf_counter()
        rows = self.run(query, **params)
        trace.append(
            {
                "step": step,
                "cypher": query.strip(),
                "params": {k: v for k, v in params.items()},
                "rows": len(rows),
                "ms": round((time.perf_counter() - start) * 1000, 1),
            }
        )
        return rows

    # ---- schema / admin --------------------------------------------------- #
    def create_constraints(self) -> None:
        for stmt in CONSTRAINTS:
            self.run(stmt)

    def reset(self) -> None:
        self.run(
            "MATCH (n) WHERE any(l IN labels(n) WHERE l IN $labels) DETACH DELETE n",
            labels=LABELS,
        )

    def stats(self) -> dict[str, Any]:
        nodes = {r["label"]: r["n"] for r in self.run(Q_STATS_NODES, labels=LABELS)}
        rels = {r["rel"]: r["n"] for r in self.run(Q_STATS_RELS)}
        return {"nodes": nodes, "relationships": rels}

    # ---- retrieval -------------------------------------------------------- #
    def search(self, question: str, limit: int = 5) -> dict[str, Any]:
        trace: list[dict] = []
        keywords = extract_keywords(question)
        result: dict[str, Any] = {
            "question": question,
            "keywords": keywords,
            "papers": [],
            "related": [],
            "edges": [],
            "trace": trace,
        }
        if not keywords:
            return result

        # 1. Rank papers by keyword hits on the paper AND its connected
        #    concepts / methods / limitations (a graph-aware match).
        ranked = self._traced(
            trace, "1. Match papers via paper text + connected concepts/methods/limitations",
            Q_MATCH_PAPERS, kw=keywords, limit=limit,
        )
        if not ranked:
            return result
        scores = {r["id"]: r["score"] for r in ranked}
        ids = list(scores)

        # 2. Traverse outward from the matched papers.
        details = self._traced(
            trace, "2. Traverse authors, concepts, methods, limitations, sources",
            Q_PAPER_DETAILS, ids=ids,
        )
        papers = []
        for d in details:
            paper = dict(d["paper"])
            paper["score"] = scores[paper["id"]]
            paper["authors"] = d["authors"]
            paper["concepts"] = d["concepts"]
            paper["methods"] = d["methods"]
            paper["limitations"] = d["limitations"]
            paper["sources"] = d["sources"]
            paper["excerpt"] = best_excerpt(paper.get("abstract") or "", keywords)
            papers.append(paper)
        papers.sort(key=lambda p: -p["score"])
        result["papers"] = papers

        # 3. Multi-hop: papers that share a concept/method with the matches,
        #    plus papers explicitly linked with RELATED_TO.
        shared = self._traced(
            trace, "3a. Related papers via shared concepts/methods (2 hops)",
            Q_RELATED_SHARED, ids=ids,
        )
        explicit = self._traced(
            trace, "3b. Related papers via RELATED_TO edges",
            Q_RELATED_EXPLICIT, ids=ids,
        )
        related: dict[str, dict] = {}
        for row in shared:
            pid = row["paper"]["id"]
            related[pid] = {
                "paper": row["paper"],
                "shared": row["shared"],
                "via_papers": row["via_papers"],
                "explicit": [],
            }
        for row in explicit:
            pid = row["paper"]["id"]
            entry = related.setdefault(
                pid,
                {"paper": row["paper"], "shared": [], "via_papers": [], "explicit": []},
            )
            entry["explicit"].append(
                {"from": row["via_paper"], "reason": row["reason"], "basis": row["basis"]}
            )
        result["related"] = sorted(
            related.values(), key=lambda r: -(len(r["shared"]) + 2 * len(r["explicit"]))
        )

        # 4. Pull the subgraph (for the visual explorer).
        graph_ids = ids + [r["paper"]["id"] for r in result["related"][:3]]
        result["edges"] = self._traced(
            trace, "4. Fetch subgraph edges for the relationship explorer",
            Q_EDGES, ids=graph_ids,
        )
        return result


def best_excerpt(text: str, keywords: list[str]) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    if not sentences or not sentences[0]:
        return ""
    scored = [(sum(k in s.lower() for k in keywords), i, s) for i, s in enumerate(sentences)]
    scored.sort(key=lambda t: (-t[0], t[1]))
    return scored[0][2]
