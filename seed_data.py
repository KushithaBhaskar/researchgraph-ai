"""Curated seed dataset + loader for ResearchGraph AI.

DATA PROVENANCE (please read):
* Paper titles, years, and arXiv URLs are real, publicly listed arXiv papers.
  Author lists are given from the curator's knowledge: verify against the
  arXiv page (linked on every paper) before presenting.
* The `abstract` field is a SHORT CURATOR SUMMARY written in our own words. It
  is NOT the paper's official abstract and is not a direct quotation.
* Concepts, methods, limitations and RELATED_TO links are CURATOR-ASSIGNED
  annotations, labelled with a `basis` property. They are illustrative
  groupings for graph discovery, not claims verified by the paper authors.

Run directly to seed:  python seed_data.py [--reset]
"""
from __future__ import annotations

import sys

from graph_db import GraphDB, load_config

CURATOR = "curator-note (verify against paper)"

CONCEPTS = {
    "Long-term memory": "Persisting information beyond a single LLM context window or session.",
    "Context window management": "Deciding what information to keep inside a limited prompt.",
    "Episodic memory": "Storing records of specific past experiences or interactions.",
    "Reflection": "Summarising or critiquing past experience into reusable higher-level insight.",
    "Procedural memory / skills": "Reusable behaviours or skills an agent stores and recalls.",
    "Retrieval-augmented generation": "Conditioning generation on documents retrieved from an external store.",
    "Memory forgetting and consolidation": "Updating, strengthening or decaying memories over time.",
    "Cognitive architecture": "Framework organising an agent's memory, actions and decision-making.",
    "Long-context failure modes": "Ways models under-use information placed in long prompts.",
    "Memory survey": "Overview and taxonomy of memory mechanisms in LLM agents.",
}

METHODS = {
    "Virtual context management": "Operating-system-inspired paging of information between a small prompt and external storage.",
    "Memory stream with recency/importance/relevance retrieval": "Log of agent experiences retrieved by a weighted score.",
    "Verbal reflection buffer": "Natural-language self-reflections stored and reused on later attempts.",
    "Executable skill library": "Growing library of verified, reusable code skills retrieved for new tasks.",
    "Forgetting-curve memory updating": "Memory strength updated with a forgetting-curve-inspired rule.",
    "Dense retrieval over external memory": "Neural retriever fetching passages from a non-parametric index.",
    "Extract-and-update memory pipeline": "LLM extracts salient facts from conversation and updates a memory store.",
    "Position-sensitivity analysis": "Controlled study of how answer accuracy varies with evidence position in the prompt.",
    "Taxonomy and literature review": "Systematic categorisation of published work.",
    "Modular agent framework": "Conceptual decomposition of agents into memory modules, action space and decision loop.",
}

PAPERS = [
    {
        "id": "arxiv:2310.08560",
        "title": "MemGPT: Towards LLMs as Operating Systems",
        "year": 2023,
        "url": "https://arxiv.org/abs/2310.08560",
        "authors": ["Charles Packer", "Sarah Wooders", "Kevin Lin", "Vivian Fang",
                    "Shishir G. Patil", "Ion Stoica", "Joseph E. Gonzalez"],
        "abstract": "Curator summary: Proposes managing an LLM's limited context like an operating system manages memory, "
                    "moving information between a fast in-prompt tier and external storage. The goal is to give "
                    "agents an effectively unbounded memory for long conversations and large documents.",
        "concepts": ["Long-term memory", "Context window management"],
        "methods": ["Virtual context management"],
        "limitations": ["Depends on the underlying LLM reliably issuing the memory-management function calls; weaker models may do this poorly."],
        "related": [("arxiv:2005.11401", "Both extend what an LLM can draw on beyond its prompt using external storage/retrieval."),
                    ("arxiv:2307.03172", "Long-context weaknesses motivate managing what goes into the prompt.")],
    },
    {
        "id": "arxiv:2304.03442",
        "title": "Generative Agents: Interactive Simulacra of Human Behavior",
        "year": 2023,
        "url": "https://arxiv.org/abs/2304.03442",
        "authors": ["Joon Sung Park", "Joseph C. O'Brien", "Carrie J. Cai",
                    "Meredith Ringel Morris", "Percy Liang", "Michael S. Bernstein"],
        "abstract": "Curator summary: Simulates believable agents that keep a natural-language record of their experiences, "
                    "retrieve relevant memories using recency, importance and relevance, and periodically reflect "
                    "to form higher-level conclusions that guide planning.",
        "concepts": ["Long-term memory", "Episodic memory", "Reflection"],
        "methods": ["Memory stream with recency/importance/relevance retrieval"],
        "limitations": ["Agents can embellish or hallucinate memories, and running many LLM-driven agents is costly."],
        "related": [("arxiv:2303.11366", "Both use reflection over stored experience to guide later behaviour."),
                    ("arxiv:2305.10250", "Both retrieve and update an agent's stored interaction history.")],
    },
    {
        "id": "arxiv:2303.11366",
        "title": "Reflexion: Language Agents with Verbal Reinforcement Learning",
        "year": 2023,
        "url": "https://arxiv.org/abs/2303.11366",
        "authors": ["Noah Shinn", "Federico Cassano", "Edward Berman", "Ashwin Gopinath",
                    "Karthik Narasimhan", "Shunyu Yao"],
        "abstract": "Curator summary: Agents improve across attempts by writing verbal reflections on feedback and keeping "
                    "them in an episodic memory buffer that is added to the prompt in later trials, instead of "
                    "updating model weights.",
        "concepts": ["Episodic memory", "Reflection"],
        "methods": ["Verbal reflection buffer"],
        "limitations": ["Keeps reflections in a bounded memory and depends on the LLM's ability to judge its own attempts; improvement is not guaranteed."],
        "related": [("arxiv:2305.16291", "Both let an agent improve from environment feedback without weight updates.")],
    },
    {
        "id": "arxiv:2305.16291",
        "title": "Voyager: An Open-Ended Embodied Agent with Large Language Models",
        "year": 2023,
        "url": "https://arxiv.org/abs/2305.16291",
        "authors": ["Guanzhi Wang", "Yuqi Xie", "Yunfan Jiang", "Ajay Mandlekar",
                    "Chaowei Xiao", "Yuke Zhu", "Linxi Fan", "Anima Anandkumar"],
        "abstract": "Curator summary: A Minecraft agent that stores verified, executable skills in a growing library and "
                    "retrieves them for new tasks, using an automatic curriculum and iterative prompting with "
                    "environment feedback.",
        "concepts": ["Procedural memory / skills", "Long-term memory"],
        "methods": ["Executable skill library"],
        "limitations": ["Relies on a costly proprietary LLM and generated code can be wrong; evaluated in a single environment (Minecraft)."],
        "related": [],
    },
    {
        "id": "arxiv:2005.11401",
        "title": "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks",
        "year": 2020,
        "url": "https://arxiv.org/abs/2005.11401",
        "authors": ["Patrick Lewis", "Ethan Perez", "Aleksandra Piktus", "Fabio Petroni",
                    "Vladimir Karpukhin", "Naman Goyal", "Heinrich Küttler", "Mike Lewis",
                    "Wen-tau Yih", "Tim Rocktäschel", "Sebastian Riedel", "Douwe Kiela"],
        "abstract": "Curator summary: Combines a generator with a dense retriever over an external text index so the model "
                    "can condition on retrieved passages, serving as a non-parametric memory for knowledge-intensive tasks.",
        "concepts": ["Retrieval-augmented generation", "Long-term memory"],
        "methods": ["Dense retrieval over external memory"],
        "limitations": ["Output quality is bounded by what the retriever surfaces from the index."],
        "related": [],
    },
    {
        "id": "arxiv:2305.10250",
        "title": "MemoryBank: Enhancing Large Language Models with Long-Term Memory",
        "year": 2023,
        "url": "https://arxiv.org/abs/2305.10250",
        "authors": ["Wanjun Zhong", "Lianghong Guo", "Qiqi Gao", "He Ye", "Yanlin Wang"],
        "abstract": "Curator summary: A long-term memory mechanism that stores past conversations and summaries and updates "
                    "memory strength with a forgetting-curve-inspired rule; demonstrated in a companion chatbot.",
        "concepts": ["Long-term memory", "Memory forgetting and consolidation"],
        "methods": ["Forgetting-curve memory updating"],
        "limitations": ["Demonstrated mainly through one companion-chatbot application."],
        "related": [],
    },
    {
        "id": "arxiv:2504.19413",
        "title": "Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory",
        "year": 2025,
        "url": "https://arxiv.org/abs/2504.19413",
        "authors": ["Prateek Chhikara", "Dev Khant", "Saket Aryan", "Taranjeet Singh", "Deshraj Yadav"],
        "abstract": "Curator summary: Presents a memory architecture that extracts salient facts from conversations and "
                    "updates a persistent store, aiming at low-latency, low-cost long-term memory for production agents.",
        "concepts": ["Long-term memory", "Memory forgetting and consolidation"],
        "methods": ["Extract-and-update memory pipeline"],
        "limitations": ["Evaluated on conversational-memory benchmarks; results may not transfer to other agent settings."],
        "related": [("arxiv:2310.08560", "Both give LLM agents persistent memory beyond the prompt, with different mechanisms.")],
    },
    {
        "id": "arxiv:2307.03172",
        "title": "Lost in the Middle: How Language Models Use Long Contexts",
        "year": 2023,
        "url": "https://arxiv.org/abs/2307.03172",
        "authors": ["Nelson F. Liu", "Kevin Lin", "John Hewitt", "Ashwin Paranjape",
                    "Michele Bevilacqua", "Fabio Petroni", "Percy Liang"],
        "abstract": "Curator summary: Analyses how accuracy changes with the position of relevant information inside long "
                    "prompts and finds models often use information at the start or end better than the middle.",
        "concepts": ["Long-context failure modes", "Context window management"],
        "methods": ["Position-sensitivity analysis"],
        "limitations": ["Diagnoses a long-context weakness but does not itself provide a persistent memory mechanism."],
        "related": [],
    },
    {
        "id": "arxiv:2309.02427",
        "title": "Cognitive Architectures for Language Agents",
        "year": 2023,
        "url": "https://arxiv.org/abs/2309.02427",
        "authors": ["Theodore R. Sumers", "Shunyu Yao", "Karthik Narasimhan", "Thomas L. Griffiths"],
        "abstract": "Curator summary: Proposes CoALA, a conceptual framework describing language agents through modular "
                    "memory components, a structured action space and a decision-making loop.",
        "concepts": ["Cognitive architecture", "Long-term memory", "Episodic memory", "Procedural memory / skills"],
        "methods": ["Modular agent framework"],
        "limitations": ["A conceptual framework; it does not itself benchmark memory designs."],
        "related": [("arxiv:2304.03442", "Frames systems such as generative agents within a common memory/action vocabulary.")],
    },
    {
        "id": "arxiv:2404.13501",
        "title": "A Survey on the Memory Mechanism of Large Language Model based Agents",
        "year": 2024,
        "url": "https://arxiv.org/abs/2404.13501",
        "authors": ["Zeyu Zhang", "Xiaohe Bo", "Chen Ma", "Rui Li", "Xu Chen",
                    "Quanyu Dai", "Jieming Zhu", "Zhenhua Dong", "Ji-Rong Wen"],
        "abstract": "Curator summary: Surveys how memory is designed, evaluated and applied in LLM-based agents, "
                    "organising prior work into a taxonomy of memory mechanisms.",
        "concepts": ["Memory survey", "Long-term memory"],
        "methods": ["Taxonomy and literature review"],
        "limitations": ["A survey: it summarises literature rather than proposing a tested memory system."],
        "related": [("arxiv:2309.02427", "Both organise the design space of agent memory at a conceptual level.")],
    },
]

EXAMPLE_QUESTIONS = [
    "Which approaches to AI agent memory have been explored, what are their limitations, and which related research papers discuss alternative approaches?",
    "How do reflection and skill libraries help agents learn from experience?",
    "What goes wrong with long context windows, and which memory methods address it?",
]


def seed_database(db: GraphDB, reset: bool = False) -> dict[str, int]:
    """Idempotently load the curated dataset with MERGE."""
    if reset:
        db.reset()
    db.create_constraints()

    for name, desc in CONCEPTS.items():
        db.run("MERGE (c:Concept {name:$name}) SET c.description=$desc", name=name, desc=desc)
    for name, desc in METHODS.items():
        db.run("MERGE (m:Method {name:$name}) SET m.description=$desc", name=name, desc=desc)

    for p in PAPERS:
        source_title = f"arXiv listing: {p['title']}"
        db.run(
            """
            MERGE (p:Paper {id:$id})
            SET p.title=$title, p.year=$year, p.abstract=$abstract,
                p.source='arXiv', p.url=$url, p.record_type='curated-seed'
            MERGE (s:ResearchSource {url:$url})
            SET s.title=$source_title
            MERGE (p)-[:SUPPORTED_BY]->(s)
            """,
            id=p["id"], title=p["title"], year=p["year"], abstract=p["abstract"],
            url=p["url"], source_title=source_title,
        )
        db.run(
            """
            MATCH (p:Paper {id:$id})
            UNWIND $authors AS an
            MERGE (a:Author {name:an})
            MERGE (p)-[:AUTHORED_BY]->(a)
            """,
            id=p["id"], authors=p["authors"],
        )
        db.run(
            """
            MATCH (p:Paper {id:$id})
            UNWIND $names AS n
            MATCH (c:Concept {name:n})
            MERGE (p)-[:COVERS]->(c)
            """,
            id=p["id"], names=p["concepts"],
        )
        db.run(
            """
            MATCH (p:Paper {id:$id})
            UNWIND $names AS n
            MATCH (m:Method {name:n})
            MERGE (p)-[:USES_METHOD]->(m)
            """,
            id=p["id"], names=p["methods"],
        )
        for i, text in enumerate(p["limitations"]):
            db.run(
                """
                MATCH (p:Paper {id:$pid})
                MERGE (l:Limitation {id:$lid})
                SET l.description=$text, l.basis=$basis
                MERGE (p)-[:HAS_LIMITATION]->(l)
                """,
                pid=p["id"], lid=f"{p['id']}#L{i}", text=text, basis=CURATOR,
            )

    for p in PAPERS:
        for other_id, reason in p["related"]:
            db.run(
                """
                MATCH (a:Paper {id:$a}), (b:Paper {id:$b})
                MERGE (a)-[r:RELATED_TO]->(b)
                SET r.reason=$reason, r.basis='curator-assigned (not an author-stated citation)'
                """,
                a=p["id"], b=other_id, reason=reason,
            )

    stats = db.stats()
    return {**stats["nodes"], "relationships_total": sum(stats["relationships"].values())}


if __name__ == "__main__":
    graph = GraphDB(**load_config())
    graph.verify()
    summary = seed_database(graph, reset="--reset" in sys.argv)
    print("Seed complete:", summary)
    graph.close()
