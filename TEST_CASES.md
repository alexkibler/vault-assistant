# Query Endpoint Test Cases

Test the `/query` endpoint with varying specificity levels to confirm RAG works correctly.

## Test Setup

```bash
# Start API
uv run uvicorn main:app --host 0.0.0.0 --port 8765

# In another terminal, run tests:
curl -X POST http://localhost:8765/query \
  -H "Content-Type: application/json" \
  -d '{"text": "YOUR_QUERY_HERE", "top_k": 5}'
```

---

## Test Cases

### Category: WORK / PANTHERX PROJECT

#### TC-1: Specific Technical Implementation Detail
**Query:** "What is the IVendorModule pattern used in Pantherx?"
- **Expected:** Returns context about DI registration and vendor module implementation
- **Sources:** Should include Pantherx.Integration.Unified.md
- **Specificity:** HIGH

#### TC-2: Vague Project Reference
**Query:** "Tell me about my .NET project"
- **Expected:** Returns Pantherx info (vendor modules, cron scheduling, etc.)
- **Sources:** Should find Pantherx files
- **Specificity:** LOW-MEDIUM (generic but should narrow to .NET context)

#### TC-3: Architecture Pattern
**Query:** "How do I handle multiple vendors in one codebase?"
- **Expected:** Returns the vendor module pattern explanation
- **Sources:** Pantherx.Integration.Unified.md
- **Specificity:** MEDIUM (concept-based rather than exact keywords)

#### TC-4: Task Name
**Query:** "What are Consumer and AdverseEvent tasks?"
- **Expected:** Task runner explanation, cron scheduling
- **Sources:** Pantherx files
- **Specificity:** MEDIUM-HIGH

---

### Category: CYCLING / HARDWARE

#### TC-5: Exact Product Specification
**Query:** "What bike do I ride?"
- **Expected:** Trek Checkpoint ALR 4 with exact specs
- **Sources:** Cycling.md
- **Specificity:** HIGH

#### TC-6: Component Details
**Query:** "What cassette do I have on my bike?"
- **Expected:** Sunrace 11-51T cassette with Garbaruk extender
- **Sources:** Cycling.md
- **Specificity:** HIGH

#### TC-7: Vague Bike Reference
**Query:** "My gravel setup"
- **Expected:** Full bike config (Trek, drivetrain, tires)
- **Sources:** Cycling.md
- **Specificity:** LOW-MEDIUM

#### TC-8: Maintenance Warning
**Query:** "What should I not change on my drivetrain?"
- **Expected:** "This drivetrain is dialed — do not touch it"
- **Sources:** Cycling.md
- **Specificity:** MEDIUM

---

### Category: TECHNICAL INFRASTRUCTURE

#### TC-9: Specific Service Query
**Query:** "How do I configure Ollama?"
- **Expected:** Should find relevant AI/infra docs if they exist
- **Sources:** Technical infrastructure files
- **Specificity:** MEDIUM-HIGH

#### TC-10: Vague Infrastructure
**Query:** "What's my homelab setup?"
- **Expected:** Docker, services, infrastructure overview
- **Sources:** Technical context files
- **Specificity:** LOW

---

### Category: MEETINGS / TIME-SENSITIVE

#### TC-11: Recent Meeting
**Query:** "What did I learn from the Patient Creation walkthrough with Jonathan?"
- **Expected:** Returns specific meeting notes
- **Sources:** "2026-06-16 Patient Creation Walkthrough with Jonathan.md"
- **Specificity:** HIGH

#### TC-12: Training Notes
**Query:** "Tell me about the McDermott ride analysis"
- **Expected:** Training session insights
- **Sources:** "2026-06-16 Training Analysis - McDermott 3-State Tour.md"
- **Specificity:** HIGH

#### TC-13: Vague Recent Event
**Query:** "What happened on my last training session?"
- **Expected:** Should return recent training notes
- **Sources:** Recent .md files with training/activity content
- **Specificity:** LOW-MEDIUM

---

### Category: EDGE CASES

#### TC-14: Multiple Word Acronym
**Query:** "What is PantherX?"
- **Expected:** Returns Pantherx work project info
- **Sources:** Pantherx files
- **Specificity:** MEDIUM

#### TC-15: Synonym/Related Concept
**Query:** "How do I handle patient data sync?"
- **Expected:** Returns Pantherx (patient data integration)
- **Sources:** Pantherx files
- **Specificity:** MEDIUM (semantic match, not keyword)

#### TC-16: Non-Existent Content
**Query:** "How do I make a sourdough starter?"
- **Expected:** "Nothing relevant found" or unrelated results
- **Sources:** None or irrelevant
- **Specificity:** EDGE CASE - should handle gracefully

#### TC-17: Very Vague Query
**Query:** "Stuff I need to remember"
- **Expected:** Likely returns some notes, but results may be low-relevance
- **Sources:** Multiple unrelated files
- **Specificity:** VERY LOW

#### TC-18: Technical Jargon
**Query:** "DI and dependency injection patterns"
- **Expected:** Should find Pantherx IVendorModule discussion
- **Sources:** Pantherx files
- **Specificity:** MEDIUM (technical term matching)

---

## Evaluation Criteria

For each test, verify:

1. **Relevance**: Are returned sources actually related to the query?
2. **Accuracy**: Does the LLM answer match what's in the sources?
3. **Source Quality**: Are the top sources the most relevant?
4. **Graceful Degradation**: Does it handle non-existent queries well?
5. **Semantic Understanding**: Does it find related concepts, not just keywords?

## Example Success Response

```json
{
  "answer": "You ride a 2024 Trek Checkpoint ALR 4 gravel bike with a 1x11 mullet drivetrain...",
  "sources": [
    "Life/Cycling/Cycling.md"
  ]
}
```

## Running All Tests

```bash
# Create test script
cat > /tmp/query_tests.sh << 'EOF'
#!/bin/bash
tests=(
  "What is the IVendorModule pattern used in Pantherx?"
  "Tell me about my .NET project"
  "What bike do I ride?"
  "What cassette do I have on my bike?"
  "What did I learn from the Patient Creation walkthrough with Jonathan?"
  "How do I handle patient data sync?"
  "How do I make a sourdough starter?"
)

for test in "${tests[@]}"; do
  echo "QUERY: $test"
  curl -s -X POST http://localhost:8765/query \
    -H "Content-Type: application/json" \
    -d "{\"text\": \"$test\", \"top_k\": 3}" | jq '.answer' | head -3
  echo ""
done
EOF

bash /tmp/query_tests.sh
```
