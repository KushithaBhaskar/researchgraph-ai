# ResearchGraph AI — Evidence-Linked Research Discovery

A Streamlit app backed by a **real Neo4j graph**. It connects papers, authors, concepts, methods,
limitations and sources to answer multi-hop questions about AI agent memory. Every answer is built
from records returned by Cypher queries, and the app shows the exact Cypher it ran.

## Graph schema
Nodes: `Paper`, `Author`, `Concept`, `Method`, `Limitation`, `ResearchSource`
Relationships: `AUTHORED_BY`, `COVERS`, `USES_METHOD`, `HAS_LIMITATION`, `RELATED_TO`, `SUPPORTED_BY`
Uniqueness constraints on every node type; all writes use `MERGE` (re-seeding never duplicates).

## Data provenance (important)
- Paper titles, years and arXiv URLs are real listings. Author lists are from the curator's
  knowledge, so verify them on the linked arXiv page before presenting.
- The `abstract` field is a short **curator summary in our own words**, not the official abstract.
- Concepts, methods, limitations and `RELATED_TO` edges are **curator-assigned annotations**
  (labelled with a `basis` property). They are not verified by the paper authors.
- If no evidence matches a question, the app says so and generates no answer.

## 1. Create a Neo4j AuraDB instance
1. Go to https://console.neo4j.io and sign in.
2. **New instance** → choose **AuraDB Free** → create.
3. **Save the generated password / download the credentials file.** It is shown only once.
4. Wait until the instance status is **Running**. Note the connection URI (`neo4j+s://…`).
   Free instances pause when idle; resume from the console if needed.

## 2. Install dependencies (Python 3.11)
```bash
cd researchgraph-ai
python3.11 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Configure environment variables locally
```bash
cp .env.example .env             # Windows: copy .env.example .env
```
Edit `.env`: set `NEO4J_URI`, `NEO4J_USERNAME` (usually `neo4j`), `NEO4J_PASSWORD`.
`ANTHROPIC_API_KEY` is optional.

## 4. Initialize the graph
```bash
python seed_data.py              # add --reset to wipe our node types first
```
Expected output: `Seed complete: {...}` with 10 Paper nodes. (You can also use the sidebar button in the app.)

## 5. Run locally
```bash
streamlit run app.py
```

## 6. Verify real Cypher is executing
- Sidebar shows **Connected to Neo4j** with live node/relationship counts.
- After a search, open the **Sources & Cypher** tab: every step lists its Cypher text, parameters,
  row count and milliseconds.
- In the Neo4j Aura console → **Query**, run `MATCH (n) RETURN labels(n)[0], count(*)` and compare
  with the sidebar counts.
- Stop the database (or change the password) and press **Retry connection**: the app should show a
  clear error rather than any answer.

## 7. Push to GitHub
```bash
git init
git add .
git status                       # confirm .env is NOT listed
git commit -m "ResearchGraph AI"
git branch -M main
git remote add origin https://github.com/<you>/researchgraph-ai.git
git push -u origin main
```

## 8. Streamlit Community Cloud secrets
1. https://share.streamlit.io → **Create app** → pick your repo, branch `main`, main file `app.py`.
2. **Advanced settings** → Python version 3.11 → **Secrets**, paste:
```toml
NEO4J_URI = "neo4j+s://xxxxxxxx.databases.neo4j.io"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "your-password"
# optional
ANTHROPIC_API_KEY = ""
```

## 9. Deploy
Click **Deploy**. Streamlit installs `requirements.txt` and gives you a public URL.
The database must already be seeded (step 4), or use the sidebar **Initialize** button once.

## 10. Test the public URL before submitting
Open it in a private window and run the checklist below.

## Test checklist
- [ ] Sidebar shows Connected and non-zero counts
- [ ] Demo question 1 returns ≥ 4 papers, limitations, and related papers
- [ ] Demo question 2 returns Reflexion, Voyager and related papers
- [ ] Graph explorer renders; arrows are labelled with relationship names
- [ ] "Sources & Cypher" shows 5 Cypher steps with row counts
- [ ] Nonsense question (e.g. "quantum banana pricing") shows "No supporting evidence found"
- [ ] No `.env` or secrets in the GitHub repo

## Demo questions (multi-hop)
1. *Which approaches to AI agent memory have been explored, what are their limitations, and which related research papers discuss alternative approaches?*
   Papers → methods/limitations → shared concepts → related papers (e.g. RAG, survey, CoALA).
2. *How do reflection and skill libraries help agents learn from experience?*
   Reflexion / Generative Agents (Reflection) → Voyager (skill library) via RELATED_TO and shared concepts.
3. *What goes wrong with long context windows, and which memory methods address it?*
   Lost in the Middle → Context window management ← MemGPT.

## Files
`app.py` UI and answers · `graph_db.py` Neo4j driver, constraints, Cypher retrieval ·
`seed_data.py` curated data + loader · `requirements.txt` · `.env.example` · `.gitignore`
