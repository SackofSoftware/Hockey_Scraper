# ⚡ Quick Start: LLM Improvement

## Run Complete Workflow (One Command)

```bash
python3 run_improvement_workflow.py
```

That's it! This will:
- ✅ Test your LLM (find failures)
- ✅ Research clubs with AI (gather context)
- ✅ Show integration steps
- ✅ Re-test (measure improvement)

---

## What Gets Created

| File | Purpose |
|------|---------|
| `club_knowledge_base_ai.json` | Full club data (edit this if needed) |
| `club_llm_context_ai.txt` | **Add this to your Ollama system prompt** |
| `club_quick_reference.txt` | One-line club summaries |
| `improvement_results/baseline_*.json` | Before improvement |
| `improvement_results/post_improvement_*.json` | After improvement |

---

## Integration

Copy `club_llm_context_ai.txt` into your Ollama system prompt:

```python
# In your Ollama tool
with open('club_llm_context_ai.txt', 'r') as f:
    club_context = f.read()

system_prompt = f"""
You are a hockey stats assistant.

{club_context}

Use the context above when answering questions.
"""
```

---

## Manual Steps (If Needed)

```bash
# Step 1: Test baseline
python3 test_ollama_stress.py

# Step 2: Research clubs
python3 club_deep_research_ai.py

# Step 3: Add context to Ollama (manual)
# Copy club_llm_context_ai.txt to your Ollama system prompt

# Step 4: Re-test
python3 test_ollama_stress.py
```

---

## What Gets Fixed

| Problem | Before | After |
|---------|--------|-------|
| Ambiguous queries | "show me WHK teams" → no divisions | Shows all WHK teams with divisions |
| Multi-team | "WHK U12 PK%" → fails | Asks which U12 team |
| Missing context | "where do they play" → no data | "Winchester plays at Wediko" |
| Contact info | "email for Vipers" → no info | "info@vipers.com" |

---

## Troubleshooting

**"No website found"**: Manually add to `club_knowledge_base_ai.json`

**"AI analysis failed"**: Rate limit hit, wait and retry

**"No improvement"**: Did you add context to Ollama prompt?

---

## Need Help?

See `LLM_IMPROVEMENT_GUIDE.md` for complete documentation.
