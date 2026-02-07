# 🧠 LLM Improvement Guide
## Systematically Improve Your Ollama Hockey Stats Responses

This guide shows you how to identify and fix failure points in your Ollama LLM's hockey stats queries.

---

## 🎯 The Problem

Your Ollama model might struggle with:
- **Ambiguous queries**: "show me all the WHK teams" (which division?)
- **Multi-team disambiguation**: "what's the WHK U12 PK%" (multiple U12 teams?)
- **Missing context**: Doesn't know about club facilities, programs, contact info
- **Complex reasoning**: "which team has best offense AND defense"
- **Edge cases**: No results found, wrong league, common player names

---

## 🔧 The Solution

This project provides **two complementary tools**:

### 1. **Stress Testing** (`test_ollama_stress.py`)
- Tests 8 categories of difficult queries
- Identifies exactly where your LLM fails
- Provides expected behaviors and SQL queries
- Compares baseline vs improved performance

### 2. **AI-Powered Context Research** (`club_deep_research_ai.py`)
- Scrapes club websites automatically
- Uses OpenRouter Polaris Alpha (free!) to analyze content
- Extracts structured info: programs, facilities, contact, key facts
- Generates LLM-ready context files

---

## 🚀 Quick Start (Automated Workflow)

Run the complete improvement cycle in one command:

```bash
python3 run_improvement_workflow.py
```

This will:
1. ✅ Run baseline stress test (identify failures)
2. ✅ Research all clubs with AI (gather context)
3. ✅ Show you how to integrate context into Ollama
4. ✅ Re-run stress test (measure improvement)

---

## 📖 Step-by-Step Manual Workflow

If you prefer to run each step individually:

### Step 1: Baseline Stress Test

```bash
python3 test_ollama_stress.py
```

**What it does:**
- Tests 40+ difficult queries across 8 categories
- Shows which queries your LLM handles well
- Identifies failure points (missing context, poor reasoning, etc.)
- Saves results for comparison

**Example output:**
```
[1/8] Testing: Ambiguous Queries
  ✓ "show me all the WHK teams"
    Expected: List all WHK teams with division tags
    SQL: SELECT DISTINCT team_name, division_name...

  ✗ "what's the WHK U12 team PK%"
    Expected: Should ask which U12 team
    Problem: No club context to disambiguate
```

### Step 2: AI Club Research

```bash
python3 club_deep_research_ai.py
```

**What it does:**
- Finds club websites automatically
- Scrapes content from each site
- Analyzes with AI (OpenRouter Polaris Alpha - free!)
- Extracts: about, programs, facilities, contact, key facts
- Generates 3 output files:
  - `club_knowledge_base_ai.json` (full data)
  - `club_llm_context_ai.txt` (for Ollama system prompt)
  - `club_quick_reference.txt` (one-line summaries)

**Example output:**
```
[1/25] Winchester Hockey Knights (3 teams)
  ✓ Found: https://www.winchesterhockey.com
  → Scraping website...
  → Analyzing with AI...
  ✓ Complete

Extracted:
  - About: Youth hockey organization serving Winchester, MA
  - Programs: U8, U10, U12, U14, U16, U18
  - Facilities: Wediko Ice Rink, Winchester Sports Complex
  - Contact: info@winchesterhockey.com
```

### Step 3: Integrate Context

Add the generated context to your Ollama system prompt:

**Option A: Manual Integration**
1. Open `club_llm_context_ai.txt`
2. Copy the entire content
3. Add to your Ollama system prompt or model configuration

**Option B: Programmatic Integration**
```python
# In your Ollama tool/script
import sqlite3

# Load club context
with open('club_llm_context_ai.txt', 'r') as f:
    club_context = f.read()

# Add to system prompt
system_prompt = f"""
You are a hockey statistics assistant with access to a SQLite database.

{club_context}

When answering questions, use both the database and club context above.
"""
```

**Option C: Quick Reference Lookup**
```python
# Use club_quick_reference.txt for compact lookups
# Format: Club Name - About | Programs | Team Count
```

### Step 4: Post-Improvement Test

```bash
python3 test_ollama_stress.py
```

Run the same stress test again to measure improvement!

**Compare results:**
- Baseline: "✗ No club context to disambiguate"
- After context: "✓ Correctly identified Winchester U12 team options"

---

## 📊 Test Categories

The stress test covers 8 comprehensive categories:

### 1. **Ambiguous Queries**
- Queries that need clarification
- Examples: "show me all WHK teams", "what's their PK%"
- Tests: Disambiguation, context awareness

### 2. **Multi-Team Disambiguation**
- Multiple teams with similar names
- Examples: "Vipers U12 stats" (multiple Vipers clubs)
- Tests: Club context, clarifying questions

### 3. **Complex Comparisons**
- Multi-criteria analysis
- Examples: "which team has best offense AND defense"
- Tests: Complex SQL, ranking logic

### 4. **Temporal Queries**
- Time-based questions
- Examples: "how have they been lately", "recent performance"
- Tests: Recency bias, date filtering

### 5. **Edge Cases**
- Unusual scenarios
- Examples: No results, wrong league, invalid data
- Tests: Error handling, graceful failures

### 6. **Aggregation Queries**
- COUNT, SUM, AVG operations
- Examples: "total goals this season", "average PK%"
- Tests: Aggregation functions, GROUP BY logic

### 7. **Player Queries**
- Individual player stats
- Examples: "top scorers", "Smith's stats" (common name)
- Tests: Player disambiguation, JOIN complexity

### 8. **Narrative/Conversational**
- Natural language questions
- Examples: "tell me about the top teams", "who's dominating"
- Tests: Conversational understanding, storytelling

---

## 🎯 Expected Improvements

After adding club context, expect these improvements:

| Query Type | Before Context | After Context |
|------------|---------------|---------------|
| "show me WHK teams" | Lists teams, no division info | Lists all WHK teams with divisions |
| "WHK U12 PK%" | Fails (ambiguous) | Asks which U12 team (WHK Bantam, WHK Squirt, etc.) |
| "where do they play" | No facility data | "Winchester plays at Wediko Ice Rink" |
| "contact for Vipers" | No info | "Email: info@vipers.com" |
| "what programs does X offer" | No info | "U8, U10, U12, U14, U16, U18" |

---

## 🔍 Monitoring Improvement

Track improvement over time:

```bash
# Create improvement_results/ folder automatically
python3 run_improvement_workflow.py

# Compare results
ls improvement_results/
  baseline_20250111_143022.json
  post_improvement_20250111_150133.json
```

**Metrics to track:**
- Number of queries answered correctly
- Disambiguation accuracy
- Response quality (human evaluation)
- SQL query correctness

---

## 🛠️ Customization

### Add Your Own Test Queries

Edit `test_ollama_stress.py`:

```python
def test_my_custom_category(self):
    """Test my specific use cases"""
    tests = [
        {
            "prompt": "your custom query here",
            "expected_behavior": "what should happen",
            "query": """
                SELECT ...
                FROM ...
                WHERE ...
            """
        }
    ]
    return self.run_test_category("My Custom Tests", tests)
```

### Add Manual Club Information

Edit `club_knowledge_base_ai.json` to add missing info:

```json
{
  "Winchester Hockey Knights": {
    "club_name": "Winchester Hockey Knights",
    "website_url": "https://winchesterhockey.com",
    "about": "Add your own description here",
    "programs": ["U8", "U10", "U12"],
    "facilities": ["Your rink name"],
    "contact_email": "email@example.com"
  }
}
```

Then regenerate context:

```bash
# Re-run just the context generation
python3 -c "
from club_deep_research_ai import AIClubResearcher
import json

researcher = AIClubResearcher()
with open('club_knowledge_base_ai.json', 'r') as f:
    researcher.club_data = json.load(f)
researcher.create_llm_context()
"
```

---

## 📁 File Reference

| File | Purpose | When to Use |
|------|---------|-------------|
| `test_ollama_stress.py` | Comprehensive test suite | Run before/after improvements |
| `club_deep_research_ai.py` | AI-powered club scraper | Gather context from websites |
| `run_improvement_workflow.py` | Automated workflow | Run complete improvement cycle |
| `club_knowledge_base_ai.json` | Full club data (JSON) | Review/edit club information |
| `club_llm_context_ai.txt` | LLM-ready context | Add to Ollama system prompt |
| `club_quick_reference.txt` | One-line summaries | Quick club lookups |

---

## 🚨 Troubleshooting

### "No website found for club X"
- Manually add website URL to `club_knowledge_base_ai.json`
- Re-run research with `--skip-search` flag (not implemented yet)
- Search manually and add info

### "AI analysis failed"
- OpenRouter API might be rate-limited (free tier)
- Check API key is valid
- Wait and retry (script has 2-second delays)

### "Stress test shows no improvement"
- Verify you added context to Ollama system prompt
- Check context file was generated correctly
- Test individual queries manually to debug

### "Too slow"
- Club research is intentionally rate-limited (2 sec/club)
- This respects website servers and free API limits
- Expected time: ~2-3 minutes for 25 clubs

---

## 🎓 Best Practices

1. **Run baseline first**: Always establish baseline before changes
2. **Review AI extractions**: Check `club_knowledge_base_ai.json` for accuracy
3. **Iterate**: Add manual corrections, re-run tests
4. **Track over time**: Save timestamped results for comparison
5. **Add test cases**: When you find new failure modes, add them to stress test
6. **Monitor API usage**: OpenRouter Polaris Alpha is free but has limits

---

## 📞 Next Steps

1. **Run the workflow**:
   ```bash
   python3 run_improvement_workflow.py
   ```

2. **Review results**:
   - Check baseline test output
   - Review `club_knowledge_base_ai.json`
   - Verify `club_llm_context_ai.txt` looks good

3. **Integrate context**:
   - Add to Ollama system prompt
   - Or load programmatically in your tools

4. **Re-test**:
   ```bash
   python3 test_ollama_stress.py
   ```

5. **Iterate**:
   - Add missing club info manually
   - Add new test cases for your specific use cases
   - Re-run periodically as data changes

---

**Happy testing! 🏒📊**
