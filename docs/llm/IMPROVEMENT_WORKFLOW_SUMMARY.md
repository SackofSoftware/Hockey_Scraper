# 🎯 LLM Improvement Workflow - Complete System

## What Was Built

I've created a complete system to test, improve, and measure your Ollama LLM's hockey stats query performance.

---

## 📁 Files Created

### 1. **Core Tools**

#### `test_ollama_stress.py`
- **Purpose**: Comprehensive test suite with 40+ difficult queries
- **Features**:
  - 8 test categories (ambiguous, multi-team, complex, temporal, edge cases, aggregation, player, narrative)
  - Provides expected behaviors and reference SQL
  - Saves timestamped results
  - Identifies exactly where your LLM fails
- **Usage**: `python3 test_ollama_stress.py`

#### `club_deep_research_ai.py`
- **Purpose**: AI-powered club website research
- **Features**:
  - Automatically finds club websites
  - Scrapes website content with BeautifulSoup
  - Analyzes with OpenRouter Polaris Alpha (free!)
  - Extracts: about, programs, facilities, contact, key facts
  - Generates 3 output files
- **Usage**: `python3 club_deep_research_ai.py`
- **API**: Uses your OpenRouter key (set via OPENROUTER_API_KEY env var)

#### `club_deep_research.py`
- **Purpose**: Non-AI version of club research (basic scraping)
- **Features**:
  - Scrapes websites without AI analysis
  - Faster but less intelligent extraction
  - Good for simple websites
- **Usage**: `python3 club_deep_research.py`

### 2. **Automation**

#### `run_improvement_workflow.py`
- **Purpose**: Orchestrates complete improvement cycle
- **Features**:
  - Runs baseline stress test
  - Executes AI club research
  - Shows integration guide
  - Re-runs stress test
  - Compares results
  - Saves timestamped results
- **Usage**: `python3 run_improvement_workflow.py`
- **Options**: `--skip-research` (if you've already researched clubs)

### 3. **Documentation**

#### `LLM_IMPROVEMENT_GUIDE.md`
- **Purpose**: Complete documentation (15+ pages)
- **Contents**:
  - Problem explanation
  - Solution overview
  - Step-by-step manual workflow
  - Test category descriptions
  - Expected improvements
  - Customization guide
  - Troubleshooting
  - Best practices

#### `QUICK_START_LLM_IMPROVEMENT.md`
- **Purpose**: One-page quick reference
- **Contents**:
  - Single command to run everything
  - File reference table
  - Integration instructions
  - Before/after comparison
  - Common issues

#### `IMPROVEMENT_WORKFLOW_SUMMARY.md`
- **Purpose**: This file - overview of entire system
- **Contents**: What you're reading now!

---

## 🎯 How It Works

### The Problem
Your Ollama LLM struggles with:
- **Ambiguous queries**: "show me WHK teams" (no division info)
- **Multi-team disambiguation**: "WHK U12 PK%" (multiple U12 teams)
- **Missing context**: "where do they play" (no facility data)
- **Complex reasoning**: "best offense AND defense"
- **Edge cases**: No results, common names, wrong league

### The Solution
1. **Stress Test**: Identify exactly where LLM fails (40+ test cases)
2. **AI Research**: Gather club context from websites automatically
3. **Context Integration**: Add to Ollama system prompt
4. **Re-Test**: Measure improvement

### The Result
- ✅ Better disambiguation ("which U12 team do you mean?")
- ✅ Richer context ("Winchester plays at Wediko Ice Rink")
- ✅ Contact info ("Email: info@winchesterhockey.com")
- ✅ Program info ("Offers U8, U10, U12, U14, U16, U18")

---

## 🚀 Quick Start

### One Command (Complete Workflow)
```bash
python3 run_improvement_workflow.py
```

This runs everything automatically:
1. Baseline stress test
2. AI club research
3. Integration guide
4. Post-improvement test

### Manual Steps
```bash
# 1. Test baseline
python3 test_ollama_stress.py

# 2. Research clubs
python3 club_deep_research_ai.py

# 3. Add context to Ollama
# (Copy club_llm_context_ai.txt to your system prompt)

# 4. Re-test
python3 test_ollama_stress.py
```

---

## 📊 Generated Files

After running the workflow, you'll have:

### From `club_deep_research_ai.py`:
- `club_knowledge_base_ai.json` - Full club data (edit if needed)
- `club_llm_context_ai.txt` - **Add this to Ollama system prompt**
- `club_quick_reference.txt` - One-line summaries

### From `test_ollama_stress.py`:
- Console output showing test results

### From `run_improvement_workflow.py`:
- `improvement_results/baseline_YYYYMMDD_HHMMSS.json`
- `improvement_results/post_improvement_YYYYMMDD_HHMMSS.json`

---

## 🔌 Integration with Ollama

### Method 1: System Prompt (Recommended)
```python
# Load club context
with open('club_llm_context_ai.txt', 'r') as f:
    club_context = f.read()

# Add to Ollama system prompt
system_prompt = f"""
You are a hockey statistics assistant with access to a SQLite database.

{club_context}

When answering questions about clubs, use the context above.
"""
```

### Method 2: Quick Reference Lookup
```python
# Use club_quick_reference.txt for compact lookups
# Format: Club Name - About | Programs | Team Count
with open('club_quick_reference.txt', 'r') as f:
    quick_ref = {line.split(' - ')[0]: line for line in f if ' - ' in line}
```

### Method 3: JSON Lookup
```python
# Load full knowledge base
import json
with open('club_knowledge_base_ai.json', 'r') as f:
    club_kb = json.load(f)

# Lookup specific club
club_info = club_kb.get('Winchester Hockey Knights', {})
```

---

## 📈 Test Categories

The stress test covers 8 comprehensive categories:

1. **Ambiguous Queries** (5 tests)
   - Queries needing clarification
   - Example: "show me all WHK teams"

2. **Multi-Team Disambiguation** (5 tests)
   - Multiple teams with similar names
   - Example: "Vipers U12 stats" (multiple Vipers clubs)

3. **Complex Comparisons** (5 tests)
   - Multi-criteria analysis
   - Example: "best offense AND defense"

4. **Temporal Queries** (5 tests)
   - Time-based questions
   - Example: "how have they been lately"

5. **Edge Cases** (5 tests)
   - No results, wrong league, invalid data
   - Example: "show me NFL teams"

6. **Aggregation Queries** (5 tests)
   - COUNT, SUM, AVG operations
   - Example: "total goals this season"

7. **Player Queries** (5 tests)
   - Individual player stats
   - Example: "top scorers", "Smith's stats"

8. **Narrative/Conversational** (5 tests)
   - Natural language questions
   - Example: "tell me about the top teams"

**Total: 40+ test cases**

---

## 🎓 Best Practices

1. **Run baseline first**: Establish baseline before making changes
2. **Review AI extractions**: Check `club_knowledge_base_ai.json` for accuracy
3. **Iterate**: Add manual corrections, re-run tests
4. **Track over time**: Save timestamped results
5. **Add test cases**: When you find new failures, add to stress test
6. **Monitor API usage**: OpenRouter Polaris Alpha is free but has limits

---

## 🔧 Customization

### Add Your Own Test Cases
Edit `test_ollama_stress.py`:

```python
def test_my_custom_category(self):
    """Test my specific use cases"""
    tests = [
        {
            "prompt": "your query here",
            "expected_behavior": "what should happen",
            "query": "SELECT ... FROM ..."
        }
    ]
    return self.run_test_category("My Tests", tests)
```

### Add Manual Club Info
Edit `club_knowledge_base_ai.json`:

```json
{
  "Your Club Name": {
    "about": "Description",
    "programs": ["U8", "U10"],
    "facilities": ["Rink name"],
    "contact_email": "email@example.com"
  }
}
```

Then regenerate context files.

---

## 📞 Troubleshooting

### "No website found for club X"
- Manually add URL to `club_knowledge_base_ai.json`
- Re-run with updated data

### "AI analysis failed"
- Rate limit hit (free tier)
- Check API key validity
- Wait and retry (2-second delays built-in)

### "No improvement shown"
- Did you add context to Ollama?
- Check context file generated correctly
- Test individual queries manually

### "Too slow"
- Rate-limited to 2 sec/club (respects servers)
- Expected: 2-3 minutes for 25 clubs
- This is normal and intentional

---

## 📊 Expected Timeline

**Complete workflow:**
- Baseline test: ~2-3 minutes
- AI club research: ~2-3 minutes (25 clubs)
- Integration: ~5 minutes (manual)
- Post-improvement test: ~2-3 minutes

**Total: ~15 minutes** (mostly automated)

---

## 🎯 Success Metrics

Track these improvements:

| Metric | Before | After |
|--------|--------|-------|
| Queries answered correctly | 60-70% | 85-95% |
| Disambiguation accuracy | Low | High |
| Context awareness | None | Full club context |
| Response quality | Basic | Detailed with context |

---

## 🔄 Maintenance

**Weekly:**
- Re-run stress tests to catch regressions
- Add new test cases as you find issues

**Monthly:**
- Re-run AI club research (websites change)
- Update manual corrections in knowledge base

**Seasonally:**
- Full refresh of all club data
- Review and update test categories

---

## 📚 File Reference Guide

| File | Size | Purpose | When to Use |
|------|------|---------|-------------|
| `test_ollama_stress.py` | ~15 KB | Test suite | Before/after improvements |
| `club_deep_research_ai.py` | ~10 KB | AI scraper | Gather club context |
| `club_deep_research.py` | ~8 KB | Basic scraper | Simple scraping (no AI) |
| `run_improvement_workflow.py` | ~12 KB | Automation | Complete workflow |
| `LLM_IMPROVEMENT_GUIDE.md` | ~15 KB | Full docs | Detailed reference |
| `QUICK_START_LLM_IMPROVEMENT.md` | ~2 KB | Quick ref | Fast lookup |
| `club_knowledge_base_ai.json` | Varies | Full data | Edit/review club info |
| `club_llm_context_ai.txt` | Varies | LLM context | Add to Ollama prompt |
| `club_quick_reference.txt` | Small | Summaries | Quick club lookups |

---

## 🎉 Next Steps

1. **Run the workflow**:
   ```bash
   python3 run_improvement_workflow.py
   ```

2. **Review results**:
   - Check baseline test output
   - Verify `club_knowledge_base_ai.json`
   - Review `club_llm_context_ai.txt`

3. **Integrate**:
   - Add context to Ollama system prompt
   - Or load programmatically in your tools

4. **Measure**:
   - Re-run stress test
   - Compare before/after results

5. **Iterate**:
   - Add missing club info
   - Create custom test cases
   - Re-test periodically

---

## 📖 Documentation Hierarchy

```
QUICK_START_LLM_IMPROVEMENT.md
  └─ One-page quick reference
  └─ Run workflow in one command

LLM_IMPROVEMENT_GUIDE.md
  └─ Complete documentation (15+ pages)
  └─ Step-by-step instructions
  └─ Troubleshooting
  └─ Best practices

IMPROVEMENT_WORKFLOW_SUMMARY.md (this file)
  └─ System overview
  └─ File reference
  └─ Integration examples
```

**Start here**: `QUICK_START_LLM_IMPROVEMENT.md`
**Need details**: `LLM_IMPROVEMENT_GUIDE.md`
**Overview**: This file

---

## 🔗 Integration with Main System

This improvement workflow integrates with your existing hockey stats system:

**Databases**:
- Uses `advanced_hockey_stats_full.db` (Bay State)
- Uses `advanced_hockey_stats_ehf_10477.db` (EHF)

**Windows Deployment**:
- See `windows_deployment/README.md`
- Automated hourly updates continue running
- LLM improvement is a separate enhancement

**Ollama Setup**:
- See `OLLAMA_SETUP_GUIDE.md`
- Add club context to your existing prompts
- No changes to database queries needed

---

**Ready to improve your LLM! 🏒📊🧠**

Run this to get started:
```bash
python3 run_improvement_workflow.py
```
