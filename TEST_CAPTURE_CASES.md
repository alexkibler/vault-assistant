# Capture Endpoint Test Cases

Test the `/capture` endpoint with notes of varying types to verify proper categorization and placement by the processor.

## Test Setup

```bash
# Terminal 1: Start API
uv run uvicorn main:app --host 0.0.0.0 --port 8765

# Terminal 2: Run capture tests
curl -X POST http://localhost:8765/capture \
  -H "Content-Type: application/json" \
  -d '{"text": "YOUR_NOTE_HERE"}'

# Terminal 3: Run processor after captures
uv run processor.py
```

---

## Test Cases

### Category: WORK / PROJECTS

#### TC-C1: Detailed Work Note
**Capture:** "Just finished implementing the vendor module DI pattern. It's clean and each vendor can now register its own services independently. Need to test with Priovant next."
- **Expected Category:** Life
- **Expected Folder:** Work/Projects
- **Reasoning:** Work project progress update, technical but personal log

#### TC-C2: Meeting Followup
**Capture:** "Meeting with Mark about infrastructure improvements. Discussed containerizing the background services and running them on the M4 mini instead of cloud VMs. Could save on costs."
- **Expected Category:** Life
- **Expected Folder:** Work
- **Reasoning:** Work meeting notes with personal decision context

#### TC-C3: Task/TODO
**Capture:** "Need to review the AdverseEvent task implementation and add better error handling for vendor-specific edge cases. Also check Calliditas consent flow."
- **Expected Category:** Life
- **Expected Folder:** Work/Projects
- **Reasoning:** Work tasks and improvements to track

---

### Category: PERSONAL / INTERESTS

#### TC-C4: Cycling Goal
**Capture:** "Thinking about upgrading to a 2x drivetrain for more climbing gear options. But the current 1x11 mullet is so dialed. Need to weigh pros and cons."
- **Expected Category:** Life
- **Expected Folder:** Cycling
- **Reasoning:** Personal cycling decision, gear considerations

#### TC-C5: Fitness Progress
**Capture:** "Crushed the McDermott 3-State Tour today. Average speed was better than last time, and the new tire setup definitely helped with grip on gravel sections."
- **Expected Category:** Life
- **Expected Folder:** Cycling & Fitness
- **Reasoning:** Personal athletic achievement and gear performance tracking

#### TC-C6: DIY/Hardware
**Capture:** "Finally got the 10-speed cassette installed correctly. The Garbaruk extender is holding up great. The chain tension is perfect. Don't change this setup."
- **Expected Category:** Life
- **Expected Folder:** Home & Property / DIY
- **Reasoning:** Personal DIY project completion

---

### Category: TECHNICAL / INFRASTRUCTURE

#### TC-C7: System Configuration
**Capture:** "Configured Ollama to run with 8GB limit in OrbStack to prevent OOM issues. Set OLLAMA_NUM_KEEP=64 for context caching. Performance is much better now."
- **Expected Category:** Context
- **Expected Folder:** Technical
- **Reasoning:** Technical infrastructure configuration, system setup

#### TC-C8: Architecture Decision
**Capture:** "Using LanceDB for vector storage instead of Pinecone. Embedded, no server needed, perfect for macOS. Chunking strategy: sections on ##/### headers, max 400 tokens per chunk."
- **Expected Category:** Context
- **Expected Folder:** Technical
- **Reasoning:** Technical architecture and design decisions

#### TC-C9: Debugging Note
**Capture:** "The watchdog thread event loop issue is happening when the vault log is created. Not critical - it's just trying to re-index the .log file. Safe to ignore."
- **Expected Category:** Context
- **Expected Folder:** Technical
- **Reasoning:** Technical debugging observation

---

### Category: PERSONAL PREFERENCES

#### TC-C10: Communication Style
**Capture:** "I prefer concise, direct responses. No fluff. Skip the preamble and get to the point. I also like when decisions include the reasoning."
- **Expected Category:** Context
- **Expected Folder:** Preferences
- **Reasoning:** Personal communication preference documentation

#### TC-C11: Tool Preference
**Capture:** "Always use uv for Python package management. It's faster than pip and handles virtual envs nicely. Never use conda."
- **Expected Category:** Context
- **Expected Folder:** Preferences
- **Reasoning:** Development tool preference

---

### Category: MISCELLANEOUS / UNCLEAR

#### TC-C12: Vague Personal Note
**Capture:** "Thinking about stuff"
- **Expected Category:** Life (fallback)
- **Expected Folder:** Projects (fallback)
- **Reasoning:** Too vague - should default safely but may be low quality

#### TC-C13: Random Observation
**Capture:** "The weather is nice today, good for riding."
- **Expected Category:** Life
- **Expected Folder:** Cycling or Personal (context-dependent)
- **Reasoning:** Personal observation with hobby context

#### TC-C14: Mixed Content (Should Pick One)
**Capture:** "Just upgraded my Docker setup to use volume mounts for Ollama models. Also got new gravel tires in the mail. Both major improvements!"
- **Expected Category:** Context or Life (mixed)
- **Expected Folder:** Technical or Cycling (mixed)
- **Reasoning:** Contains two separate topics - LLM should pick the primary one

---

## Evaluation Criteria

For each captured note, verify:

1. **Correct Categorization**: Is it in Life, Context, or Archive?
2. **Correct Subfolder**: Is it in the right place within the category?
3. **Accurate Title**: Does the generated filename match the content?
4. **Reasoning Quality**: Is the LLM's reasoning for placement sound?
5. **Metadata**: Is the frontmatter correct and complete?
6. **Content Preservation**: Is the original note text preserved?

---

## Expected Output Example

```
- **PROCESSED** `2026-06-16T19-00-00.000000_text_xxxxxxxx.md`
  - Location: [[Life/Work/Projects/Vendor Module Implementation.md]]
  - Time: 2026-06-16T19:00:15.123456
  - Reason: work-related technical project update
```

Note should exist at: `Life/Work/Projects/Vendor Module Implementation.md`

---

## Audit Checklist

After processor runs, verify each note:

- [ ] File created in correct vault location
- [ ] Frontmatter added with title, type, updated date
- [ ] Original text preserved in body
- [ ] Categorization matches expected category
- [ ] Subfolder placement makes sense
- [ ] Log entries show PROCESSED status
- [ ] No processing errors in log

---

## Running Full Test

```bash
#!/bin/bash

# Start API
uv run uvicorn main:app --host 0.0.0.0 --port 8765 &
API_PID=$!
sleep 5

# Define test notes
tests=(
  "Just finished implementing the vendor module DI pattern. It's clean and each vendor can now register its own services independently. Need to test with Priovant next."
  "Meeting with Mark about infrastructure improvements. Discussed containerizing the background services and running them on the M4 mini instead of cloud VMs. Could save on costs."
  "Thinking about upgrading to a 2x drivetrain for more climbing gear options. But the current 1x11 mullet is so dialed. Need to weigh pros and cons."
  "Crushed the McDermott 3-State Tour today. Average speed was better than last time, and the new tire setup definitely helped with grip on gravel sections."
  "Configured Ollama to run with 8GB limit in OrbStack to prevent OOM issues. Set OLLAMA_NUM_KEEP=64 for context caching. Performance is much better now."
  "I prefer concise, direct responses. No fluff. Skip the preamble and get to the point. I also like when decisions include the reasoning."
)

# Capture all
echo "=== Capturing notes ==="
for test in "${tests[@]}"; do
  curl -s -X POST http://localhost:8765/capture \
    -H "Content-Type: application/json" \
    -d "{\"text\": \"$test\"}" | jq '.saved_to'
  sleep 1
done

# Kill API
kill $API_PID 2>/dev/null

# Process
echo ""
echo "=== Processing notes ==="
uv run processor.py

# Audit
echo ""
echo "=== Vault audit ==="
echo "Notes created:"
find ~/Library/Mobile\ Documents/iCloud~md~obsidian/Documents/iCloud/Life -name "*.md" -mtime 0
find ~/Library/Mobile\ Documents/iCloud~md~obsidian/Documents/iCloud/Context -name "*.md" -mtime 0

echo ""
echo "Log entries:"
tail -30 ~/Library/Mobile\ Documents/iCloud~md~obsidian/Documents/iCloud/vault-assistant.md
```
