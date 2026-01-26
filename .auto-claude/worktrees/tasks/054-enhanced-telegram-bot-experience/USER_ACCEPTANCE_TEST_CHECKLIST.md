# User Acceptance Testing Checklist
**Feature:** Enhanced Telegram Bot Experience
**Date:** 2026-01-26
**Task:** subtask-5-3
**Phase:** Integration Testing & Verification

## Overview

This checklist verifies that all acceptance criteria from the specification are met through comprehensive manual testing. This UAT builds upon automated integration tests and performance verification to provide end-to-end validation.

**Acceptance Criteria from Spec:**
1. ✅ Inline keyboard buttons for common task actions
2. ⚠️ Voice message transcription accuracy > 95%
3. ⚠️ Screenshots can be analyzed and context extracted
4. ✅ Quick action buttons: brain dump, complete task, log energy
5. ✅ Response time < 3 seconds for common operations
6. ✅ Rich formatting in bot responses

## Prerequisites

Before beginning UAT, ensure:
- [ ] Telegram bot is running: `python Tools/telegram_bot.py`
- [ ] WorkOS database is accessible and populated with test data
- [ ] Health database (SQLite) is accessible
- [ ] Test Telegram account has bot access
- [ ] Voice recording capability available on test device
- [ ] Screenshots/images available for testing
- [ ] Timer/stopwatch available for response time measurements

---

## Test Suite

### AC1: Inline Keyboard Buttons for Common Task Actions

**Status:** ✅ Pre-verified (Integration Test Report - 67/67 checks passed)

#### Test 1.1: Task List Inline Buttons
- [ ] Send "show tasks" or click "View Tasks" from /menu
- [ ] Verify each task displays with inline buttons:
  - [ ] "✅ Complete" button
  - [ ] "📝 Details" button
- [ ] Buttons are properly formatted and aligned
- [ ] Button callbacks respond immediately (< 1s)

**Expected Result:** ✅ All tasks show inline action buttons

#### Test 1.2: Task Detail Action Buttons
- [ ] Click "Details" on any task
- [ ] Verify task detail view displays with action buttons:
  - [ ] "✅ Complete" button
  - [ ] "⏸ Postpone" button
  - [ ] "🗑 Delete" button
  - [ ] "« Back" button
- [ ] Buttons are arranged in 2 rows for easy access
- [ ] All buttons are clickable and responsive

**Expected Result:** ✅ Task details show 4 action buttons in proper layout

#### Test 1.3: Complete Task Flow
- [ ] From task list or detail view, click "Complete" button
- [ ] Verify confirmation message includes:
  - [ ] ✅ Success emoji
  - [ ] Task title
  - [ ] Priority indicator
  - [ ] Timestamp
  - [ ] "Task marked complete in WorkOS"
- [ ] Verify task is actually marked complete in WorkOS database
- [ ] Task disappears from active task list

**Expected Result:** ✅ Task is completed and confirmed with rich formatting

#### Test 1.4: Postpone Task Flow
- [ ] Click "Details" on a task, then "Postpone"
- [ ] Verify confirmation message includes:
  - [ ] ⏸ Postpone emoji
  - [ ] Task title
  - [ ] Status change to "queued"
  - [ ] Timestamp
- [ ] Verify task status updated to "queued" in WorkOS

**Expected Result:** ✅ Task is postponed with proper status update

#### Test 1.5: Delete Task Flow
- [ ] Click "Details" on a task, then "Delete"
- [ ] Verify confirmation message includes:
  - [ ] 🗑 Delete emoji
  - [ ] Task title
  - [ ] "permanently removed" confirmation
- [ ] Verify task is removed from WorkOS database
- [ ] Task no longer appears in any list

**Expected Result:** ✅ Task is deleted permanently with confirmation

**AC1 RESULT:** [ ] PASS / [ ] FAIL
**Notes:**

---

### AC2: Voice Message Transcription Accuracy > 95%

**Status:** ⚠️ Requires Manual Verification

#### Test 2.1: Clear Speech Transcription (Easy)
- [ ] Record 30-second voice message with clear speech
- [ ] Use standard vocabulary and complete sentences
- [ ] Example: "I need to schedule a meeting with Sarah on Tuesday at 3pm to discuss the quarterly budget review. Also, remind me to follow up with John about the project timeline."
- [ ] Send voice message to bot
- [ ] Compare transcription with actual words spoken
- [ ] Count errors: (wrong words + missing words + extra words)
- [ ] Calculate accuracy: (Total words - Errors) / Total words × 100

**Target:** ≥ 95% accuracy
**Word Count:** _____
**Errors:** _____
**Accuracy:** _____%
**Result:** [ ] PASS (≥95%) / [ ] FAIL (<95%)

#### Test 2.2: Complex Vocabulary Transcription (Medium)
- [ ] Record 20-second voice message with technical/domain terms
- [ ] Example: "Add task to review the asynchronous database connection pooling implementation for the Telegram bot. Also check if asyncpg and aiosqlite are properly configured."
- [ ] Send voice message to bot
- [ ] Verify transcription accuracy for technical terms
- [ ] Calculate accuracy as above

**Target:** ≥ 95% accuracy
**Word Count:** _____
**Errors:** _____
**Accuracy:** _____%
**Result:** [ ] PASS (≥95%) / [ ] FAIL (<95%)

#### Test 2.3: Ambient Noise Transcription (Hard)
- [ ] Record 15-second voice message in slightly noisy environment
- [ ] Background: light music, outdoor sounds, or office chatter
- [ ] Use natural speaking pace and volume
- [ ] Send voice message to bot
- [ ] Verify transcription handles noise gracefully
- [ ] Calculate accuracy

**Target:** ≥ 90% accuracy (relaxed for noisy conditions)
**Word Count:** _____
**Errors:** _____
**Accuracy:** _____%
**Result:** [ ] PASS (≥90%) / [ ] FAIL (<90%)

#### Test 2.4: Voice Action Buttons
- [ ] After voice transcription appears, verify action buttons:
  - [ ] "📝 Save as Task" button
  - [ ] "💡 Save as Idea" button
- [ ] Click "Save as Task" button
- [ ] Verify confirmation message includes:
  - [ ] ✅ Success indicator
  - [ ] Transcription text
  - [ ] Routing results (task created, synced to WorkOS)
  - [ ] Timestamp
- [ ] Verify task created in WorkOS with transcription as content

**Expected Result:** ✅ Voice actions work end-to-end with proper routing

#### Test 2.5: Voice Transcription Response Time
- [ ] Record 10-second voice message
- [ ] Start timer when message is sent
- [ ] Stop timer when transcription appears
- [ ] Record response time

**Target:** < 5 seconds
**Response Time:** _____s
**Result:** [ ] PASS (<5s) / [ ] FAIL (≥5s)

**AC2 OVERALL ACCURACY:**
- Test 2.1: _____%
- Test 2.2: _____%
- Test 2.3: _____%
- **Average:** _____%

**AC2 RESULT:** [ ] PASS (avg ≥95%) / [ ] FAIL (avg <95%)
**Notes:**

---

### AC3: Screenshots Can Be Analyzed and Context Extracted

**Status:** ⚠️ Requires Manual Verification

#### Test 3.1: Screenshot with Text (OCR)
- [ ] Take or select screenshot containing readable text
- [ ] Example: Screenshot of article, webpage, or document
- [ ] Send screenshot to bot (with or without caption)
- [ ] Verify bot acknowledges photo receipt
- [ ] Verify bot response includes:
  - [ ] 📸 Photo emoji indicator
  - [ ] "Photo received" confirmation
  - [ ] File size and metadata
  - [ ] Processing status
- [ ] Check if extracted text is mentioned or stored

**Expected Result:** ✅ Screenshot processed and acknowledged with rich formatting

#### Test 3.2: Screenshot with Caption Analysis
- [ ] Take screenshot of UI, diagram, or visual content
- [ ] Add caption: "UI design for new dashboard - need to implement responsive grid layout"
- [ ] Send to bot
- [ ] Verify bot processes caption through brain dump pipeline
- [ ] Verify classification and routing:
  - [ ] Caption classified (e.g., "personal_task" or "idea")
  - [ ] Routing results shown (task created or idea saved)
  - [ ] Photo saved alongside caption
- [ ] Verify task/idea created in WorkOS with caption

**Expected Result:** ✅ Caption analyzed and routed; photo attached to entry

#### Test 3.3: Multiple Screenshots in Sequence
- [ ] Send 3 different screenshots with captions in quick succession
- [ ] Screenshot 1: "Bug in login form - submit button not working"
- [ ] Screenshot 2: "Design inspiration for new homepage layout"
- [ ] Screenshot 3: "API endpoint documentation for reference"
- [ ] Verify bot processes all 3 sequentially
- [ ] Each photo gets acknowledgment and routing
- [ ] No photos are dropped or lost

**Expected Result:** ✅ All screenshots processed successfully without loss

#### Test 3.4: Screenshot Context Extraction
- [ ] Send screenshot of code snippet, error message, or technical content
- [ ] Add caption describing context
- [ ] Verify bot extracts and preserves:
  - [ ] Caption text
  - [ ] Photo metadata (size, dimensions if available)
  - [ ] Timestamp
  - [ ] Associated entry ID
- [ ] Verify screenshot can be retrieved later

**Expected Result:** ✅ Context preserved and retrievable

#### Test 3.5: Screenshot Response Time
- [ ] Send screenshot with caption
- [ ] Start timer when message is sent
- [ ] Stop timer when acknowledgment appears
- [ ] Record response time

**Target:** < 3 seconds
**Response Time:** _____s
**Result:** [ ] PASS (<3s) / [ ] FAIL (≥3s)

**AC3 RESULT:** [ ] PASS / [ ] FAIL
**Notes:**

---

### AC4: Quick Action Buttons Work

**Status:** ✅ Pre-verified (Integration Test Report)

#### Test 4.1: /menu Command Shows Quick Actions
- [ ] Send `/menu` command to bot
- [ ] Verify quick action buttons appear:
  - [ ] "🧠 Brain Dump" button
  - [ ] "⚡ Log Energy" button
  - [ ] "📋 View Tasks" button
- [ ] Buttons are properly formatted in inline keyboard
- [ ] Response time < 1 second

**Expected Result:** ✅ All 3 quick action buttons displayed

#### Test 4.2: Brain Dump Quick Action
- [ ] Click "Brain Dump" button from /menu
- [ ] Verify instruction message appears with:
  - [ ] 🧠 Brain Dump emoji
  - [ ] Text, voice, and photo options listed
  - [ ] Instructions to return to /menu
- [ ] Send text: "Remember to buy groceries: milk, eggs, bread"
- [ ] Verify processing acknowledgment with:
  - [ ] Classification (e.g., "thinking")
  - [ ] Routing results
  - [ ] Emoji indicator
  - [ ] Timestamp
- [ ] Verify entry saved to database

**Expected Result:** ✅ Brain dump flow works end-to-end

#### Test 4.3: Log Energy Quick Action
- [ ] Click "Log Energy" button from /menu
- [ ] Verify energy level buttons appear (1-10) in grid layout:
  - [ ] First row: 1, 2, 3, 4, 5
  - [ ] Second row: 6, 7, 8, 9, 10
- [ ] Click energy level "7"
- [ ] Verify confirmation message includes:
  - [ ] ⚡ Energy emoji (high energy = 🔥)
  - [ ] Energy level: "7"
  - [ ] Energy description: "Good energy"
  - [ ] Timestamp
  - [ ] "Logged to WorkOS" confirmation
- [ ] Verify energy logged to WorkOS energy_logs table
- [ ] Response time < 1 second

**Expected Result:** ✅ Energy logging works with proper feedback

#### Test 4.4: View Tasks Quick Action
- [ ] Click "View Tasks" button from /menu
- [ ] Verify active task list appears
- [ ] Each task shows:
  - [ ] Task title
  - [ ] Priority indicator
  - [ ] Inline buttons (Complete, Details)
- [ ] Response time < 2 seconds
- [ ] If no tasks: "No active tasks" message shown

**Expected Result:** ✅ Task list displays with inline buttons

#### Test 4.5: Quick Actions in Different Contexts
- [ ] Test quick actions after sending regular messages
- [ ] Test quick actions after completing other actions
- [ ] Test rapid successive clicks on quick action buttons
- [ ] Verify no state corruption or errors
- [ ] All actions work consistently

**Expected Result:** ✅ Quick actions work reliably in all contexts

**AC4 RESULT:** [ ] PASS / [ ] FAIL
**Notes:**

---

### AC5: Response Time < 3 Seconds for Common Operations

**Status:** ✅ Pre-verified (Performance Verification Report)

#### Test 5.1: Task Query Performance
- [ ] Clear any caches (restart bot if needed)
- [ ] Start timer
- [ ] Send "show tasks" or click "View Tasks"
- [ ] Stop timer when task list appears
- [ ] Record response time
- [ ] Repeat 3 times and calculate average

**Target:** < 2 seconds
**Trial 1:** _____s
**Trial 2:** _____s
**Trial 3:** _____s
**Average:** _____s
**Result:** [ ] PASS (<2s avg) / [ ] FAIL (≥2s avg)

#### Test 5.2: Brain Dump Performance
- [ ] Start timer
- [ ] Send text message: "Add task to review performance metrics"
- [ ] Stop timer when acknowledgment appears
- [ ] Record response time
- [ ] Repeat 3 times and calculate average

**Target:** < 3 seconds
**Trial 1:** _____s
**Trial 2:** _____s
**Trial 3:** _____s
**Average:** _____s
**Result:** [ ] PASS (<3s avg) / [ ] FAIL (≥3s avg)

#### Test 5.3: Energy Log Performance
- [ ] Send /menu
- [ ] Click "Log Energy"
- [ ] Start timer
- [ ] Click energy level "5"
- [ ] Stop timer when confirmation appears
- [ ] Record response time
- [ ] Repeat 3 times and calculate average

**Target:** < 1 second
**Trial 1:** _____s
**Trial 2:** _____s
**Trial 3:** _____s
**Average:** _____s
**Result:** [ ] PASS (<1s avg) / [ ] FAIL (≥1s avg)

#### Test 5.4: Task Complete Performance
- [ ] View tasks
- [ ] Start timer
- [ ] Click "Complete" on a task
- [ ] Stop timer when confirmation appears
- [ ] Record response time
- [ ] Repeat 3 times and calculate average

**Target:** < 2 seconds
**Trial 1:** _____s
**Trial 2:** _____s
**Trial 3:** _____s
**Average:** _____s
**Result:** [ ] PASS (<2s avg) / [ ] FAIL (≥2s avg)

#### Test 5.5: Load Test - Multiple Operations
- [ ] Perform 10 operations in sequence:
  - [ ] 3 task queries
  - [ ] 3 brain dumps
  - [ ] 2 energy logs
  - [ ] 2 task completions
- [ ] Record all response times
- [ ] Verify no degradation over time
- [ ] Calculate average response time

**Trial Count:** 10
**Slowest Response:** _____s
**Average Response:** _____s
**Result:** [ ] PASS (consistent performance) / [ ] FAIL (degradation observed)

**AC5 RESULT:** [ ] PASS / [ ] FAIL
**Notes:**

---

### AC6: Rich Formatting in Bot Responses

**Status:** ✅ Pre-verified (Integration Test Report - 564 italic occurrences, 90 bold headers, 115 emoji)

#### Test 6.1: Start Command Formatting
- [ ] Send `/start` command
- [ ] Verify rich formatting includes:
  - [ ] Visual separators (━━━━ lines)
  - [ ] Bold section headers (e.g., **Commands:**)
  - [ ] Emoji indicators (🧠, ⚡, 📋, etc.)
  - [ ] Proper spacing between sections
  - [ ] Indented lists (2 spaces)
  - [ ] Italic secondary info

**Expected Result:** ✅ Start message is well-formatted and readable

#### Test 6.2: Task List Formatting
- [ ] Query tasks
- [ ] Verify each task shows:
  - [ ] Bold task title
  - [ ] Priority emoji (🔴 high, 🟡 medium, 🟢 low)
  - [ ] Italic metadata (due date, tags)
  - [ ] Proper spacing between tasks
  - [ ] Overflow indicator if > 10 tasks ("...and X more")

**Expected Result:** ✅ Task list is clean and scannable

#### Test 6.3: Confirmation Message Formatting
- [ ] Complete a task
- [ ] Verify confirmation includes:
  - [ ] ✅ Success emoji at start
  - [ ] Bold header: "**Task Completed**"
  - [ ] Task title and priority
  - [ ] Italic timestamp
  - [ ] Italic secondary info ("marked complete in WorkOS")
  - [ ] Proper spacing

**Expected Result:** ✅ Confirmations are visually clear and informative

#### Test 6.4: Brain Dump Acknowledgment Formatting
- [ ] Send brain dump message
- [ ] Verify acknowledgment includes:
  - [ ] Emoji based on classification (🎯, 💡, 🤔, etc.)
  - [ ] Bold classification type
  - [ ] Indented action items (2 spaces)
  - [ ] Checkmarks (✓) for completed actions
  - [ ] Italic notes for additional context
  - [ ] Timestamp formatting

**Expected Result:** ✅ Brain dump responses are richly formatted

#### Test 6.5: Error Message Formatting
- [ ] Trigger an error (e.g., invalid input, database unavailable)
- [ ] Verify error message includes:
  - [ ] ⚠️ or ❌ error emoji
  - [ ] Bold error header
  - [ ] Clear description (no stack traces shown to user)
  - [ ] Helpful next steps or suggestions
  - [ ] Proper spacing

**Expected Result:** ✅ Error messages are user-friendly and formatted

#### Test 6.6: Health Status Formatting
- [ ] Send command for health status (if available)
- [ ] Verify formatting includes:
  - [ ] Emoji indicators for data points
  - [ ] Bold section headers
  - [ ] Proper alignment and spacing
  - [ ] Italic timestamps
  - [ ] Clear visual hierarchy

**Expected Result:** ✅ Health data is presented clearly

#### Test 6.7: Markdown Rendering
- [ ] Review all bot responses
- [ ] Verify Telegram properly renders:
  - [ ] Bold text (**text**)
  - [ ] Italic text (_text_)
  - [ ] Emoji display
  - [ ] Line breaks and spacing
  - [ ] Special characters (bullets, arrows)
- [ ] No broken formatting or escaped characters visible

**Expected Result:** ✅ All markdown renders correctly in Telegram

**AC6 RESULT:** [ ] PASS / [ ] FAIL
**Notes:**

---

## Overall UAT Results

### Acceptance Criteria Summary

| AC | Criterion | Status | Pass/Fail |
|----|-----------|--------|-----------|
| AC1 | Inline keyboard buttons for common task actions | ✅ Pre-verified | [ ] PASS / [ ] FAIL |
| AC2 | Voice message transcription accuracy > 95% | ⚠️ Manual test | [ ] PASS / [ ] FAIL |
| AC3 | Screenshots can be analyzed and context extracted | ⚠️ Manual test | [ ] PASS / [ ] FAIL |
| AC4 | Quick action buttons: brain dump, complete task, log energy | ✅ Pre-verified | [ ] PASS / [ ] FAIL |
| AC5 | Response time < 3 seconds for common operations | ✅ Pre-verified | [ ] PASS / [ ] FAIL |
| AC6 | Rich formatting in bot responses | ✅ Pre-verified | [ ] PASS / [ ] FAIL |

### Critical Issues Found

**High Priority:**
1.
2.
3.

**Medium Priority:**
1.
2.
3.

**Low Priority / Enhancement:**
1.
2.
3.

### Test Environment Details

- **Bot Version:** [Git commit hash]
- **Test Date:** [Date]
- **Tester:** [Name]
- **Test Device:** [Device type/OS]
- **Database:** [WorkOS connection status]
- **Test Duration:** [Total time spent]

### Overall Assessment

**Total Tests:** 35
**Tests Passed:** _____
**Tests Failed:** _____
**Pass Rate:** _____%

**FINAL UAT RESULT:** [ ] APPROVED / [ ] REJECTED / [ ] CONDITIONALLY APPROVED

**Tester Signature:** ___________________________
**Date:** ___________________________

---

## Appendix: Test Data

### Sample Voice Messages for Testing

**Test 2.1 - Clear Speech:**
> "I need to schedule a meeting with Sarah on Tuesday at 3pm to discuss the quarterly budget review. Also, remind me to follow up with John about the project timeline and check if the design mockups are ready for the client presentation."

**Test 2.2 - Technical Vocabulary:**
> "Add task to review the asynchronous database connection pooling implementation for the Telegram bot. Check if asyncpg and aiosqlite are properly configured with connection pool sizes of min 1 and max 5. Also verify that asyncio gather is used for parallel query execution."

**Test 2.3 - Natural Speech:**
> "Hey, just wanted to capture this idea real quick. What if we added a dark mode toggle to the app settings? I think users would really appreciate it, especially for evening use. Maybe we could also add a schedule so it switches automatically at sunset."

### Sample Screenshots for Testing

1. **Text-heavy screenshot:** Article, documentation page, or code snippet
2. **UI screenshot:** Dashboard, form, or interface mockup
3. **Diagram/Chart:** Flowchart, graph, or technical diagram
4. **Error message:** Stack trace or error dialog
5. **Mixed content:** Screenshot with text, images, and UI elements

### Sample Brain Dump Messages

1. "Buy groceries: milk, eggs, bread, coffee"
2. "Meeting notes: discussed Q1 goals, need to increase conversion by 15%"
3. "Idea: create mobile app for expense tracking"
4. "Bug report: login form submit button not responding on mobile"
5. "Research topic: best practices for API rate limiting"

---

## Reference Documentation

- **Integration Test Report:** `INTEGRATION_TEST_REPORT.md` (67/67 checks passed)
- **Performance Verification:** `RESPONSE_TIME_VERIFICATION.md` (All targets met)
- **Spec Document:** `.auto-claude/specs/054-enhanced-telegram-bot-experience/spec.md`
- **Implementation Plan:** `.auto-claude/specs/054-enhanced-telegram-bot-experience/implementation_plan.json`

---

**Document Version:** 1.0
**Last Updated:** 2026-01-26
**Status:** Ready for UAT Execution
