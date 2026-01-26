# UAT Execution Guide
**Enhanced Telegram Bot Experience - Subtask 5-3**

## Quick Start

This guide helps you execute the User Acceptance Testing checklist efficiently and systematically.

### Before You Begin

1. **Print the Checklist**
   - Open `USER_ACCEPTANCE_TEST_CHECKLIST.md`
   - Print or have it open on a second screen
   - Use checkbox format for easy tracking

2. **Prepare Test Environment**
   ```bash
   # Start the Telegram bot
   cd /Users/jeremy/Projects/Thanos
   python Tools/telegram_bot.py
   ```

3. **Verify Prerequisites**
   - [ ] Bot responds to messages
   - [ ] WorkOS database accessible
   - [ ] Voice recording works on test device
   - [ ] Timer ready for response time tests

4. **Prepare Test Data**
   - [ ] 3-5 test tasks in WorkOS database
   - [ ] 3-5 screenshot images ready
   - [ ] Voice message script prepared (see appendix in checklist)

---

## Test Execution Order

Execute tests in this order for logical flow:

### Phase 1: Basic Functionality (15 mins)
**Focus:** Quick actions and inline keyboards

1. **AC4: Quick Action Buttons** (Tests 4.1-4.5)
   - Start with /menu command
   - Test all 3 quick action buttons
   - Verify button responsiveness

2. **AC1: Inline Keyboard Buttons** (Tests 1.1-1.5)
   - Test task list buttons
   - Test task detail buttons
   - Complete/postpone/delete flows

### Phase 2: Rich Media (20 mins)
**Focus:** Voice and screenshots

3. **AC2: Voice Transcription** (Tests 2.1-2.5)
   - **CRITICAL:** This validates the 95% accuracy requirement
   - Record voice messages carefully
   - Count words and errors precisely
   - Test in different environments

4. **AC3: Screenshot Analysis** (Tests 3.1-3.5)
   - Test different screenshot types
   - Verify caption processing
   - Check context extraction

### Phase 3: Performance & UX (15 mins)
**Focus:** Speed and formatting

5. **AC5: Response Times** (Tests 5.1-5.5)
   - Use stopwatch for accurate timing
   - Run 3 trials per test for averages
   - Note any outliers

6. **AC6: Rich Formatting** (Tests 6.1-6.7)
   - Review all message types
   - Check emoji rendering
   - Verify markdown display

---

## Critical Test Focus Areas

### Voice Transcription Accuracy (AC2) ⚠️ CRITICAL

This is the **most important** manual test as it directly validates the >95% accuracy requirement.

**How to Calculate Accuracy:**

1. **Prepare Script:**
   ```
   "I need to schedule a meeting with Sarah on Tuesday at 3pm to discuss
   the quarterly budget review. Also, remind me to follow up with John
   about the project timeline."
   ```
   **Word count: 30 words**

2. **Record Voice Message:**
   - Speak clearly at normal pace
   - Record in quiet environment
   - Send to Telegram bot

3. **Compare Transcription:**
   ```
   Transcription: "I need to schedule a meeting with Sarah on Tuesday at
   3 PM to discuss the quarterly budget review. Also remind me to follow
   up with John about the project timeline."
   ```

4. **Count Errors:**
   - Wrong word: "3pm" → "3 PM" (0 errors - acceptable variation)
   - Missing word: missing comma (0 errors - punctuation doesn't count)
   - Extra word: (0 errors)
   - **Total errors: 0**

5. **Calculate:**
   - Accuracy = (30 - 0) / 30 × 100 = **100%** ✅

**Minimum Requirements:**
- Test 2.1 (Clear): ≥95% accuracy required
- Test 2.2 (Technical): ≥95% accuracy required
- Test 2.3 (Noise): ≥90% accuracy required
- **Average: ≥95% required to PASS**

**If Accuracy < 95%:**
- Document specific errors
- Test in different environments
- Check if Whisper model is properly configured
- Consider if errors are acceptable (e.g., "3pm" vs "3 PM")
- May need to adjust model or transcription pipeline

---

## Time Budgets

Plan your UAT session:

| Phase | Duration | Tests |
|-------|----------|-------|
| Setup | 10 min | Environment prep |
| Phase 1 | 15 min | AC1, AC4 (Quick actions & buttons) |
| Phase 2 | 20 min | AC2, AC3 (Voice & screenshots) |
| Phase 3 | 15 min | AC5, AC6 (Performance & formatting) |
| Documentation | 10 min | Fill results, notes |
| **Total** | **70 min** | **6 acceptance criteria** |

---

## Success Criteria

### Must Pass (Blocking)
- ✅ **AC2: Voice accuracy ≥95%** - CRITICAL requirement
- ✅ **AC5: Response times <3s** - Performance SLA
- ✅ **AC4: Quick actions work** - Core feature

### Should Pass (Important)
- ✅ **AC1: Inline keyboards work** - UX enhancement
- ✅ **AC3: Screenshots processed** - Mobile capture feature
- ✅ **AC6: Rich formatting** - Professional appearance

### Conditional Approval Allowed
If minor issues found in:
- Formatting edge cases (AC6)
- Screenshot edge cases (AC3)
- Performance outliers under heavy load (AC5)

**NOT allowed for conditional approval:**
- Voice accuracy <95% (AC2)
- Quick actions broken (AC4)
- Response times consistently >3s (AC5)

---

## Quick Test Scripts

### Script 1: Smoke Test (5 mins)
Quick validation that everything works:

```
1. Send /menu → verify 3 buttons
2. Click "Brain Dump" → send "test message"
3. Click "Log Energy" → select level 5
4. Click "View Tasks" → verify task list
5. Send voice "testing transcription"
6. Send screenshot with caption "test image"
```

**If smoke test passes:** Proceed with full UAT
**If smoke test fails:** Fix issues before full UAT

### Script 2: Voice Accuracy Test (10 mins)
Focused voice transcription validation:

```
Test 1: Clear speech
- Record: [Use script from Test 2.1]
- Count: 30 words
- Errors: _____
- Accuracy: _____%

Test 2: Technical terms
- Record: [Use script from Test 2.2]
- Count: 35 words
- Errors: _____
- Accuracy: _____%

Test 3: With noise
- Record: [Use script from Test 2.3]
- Count: 20 words
- Errors: _____
- Accuracy: _____%

Average: _____%
Result: PASS/FAIL
```

### Script 3: Performance Test (10 mins)
Time all common operations:

```bash
# Use phone stopwatch or:
date +%s.%N  # Start time (Unix timestamp with nanoseconds)
# ... perform operation ...
date +%s.%N  # End time
# Calculate: End - Start = duration
```

```
Task query: _____s (target: <2s)
Brain dump: _____s (target: <3s)
Energy log: _____s (target: <1s)
Task complete: _____s (target: <2s)
Voice (10s): _____s (target: <5s)
```

---

## Common Issues & Solutions

### Issue: Voice Accuracy Low (<95%)

**Possible Causes:**
1. Whisper model not loaded correctly
2. Audio quality poor
3. Background noise too high
4. Speaking too fast or unclear

**Solutions:**
1. Check Whisper model configuration in telegram_bot.py
2. Re-record in quieter environment
3. Speak more clearly and at moderate pace
4. Test with different voice samples
5. Review Whisper API settings (temperature, language)

**Acceptable Variations:**
- "3pm" vs "3 PM" - acceptable
- "don't" vs "do not" - acceptable
- Missing commas/periods - acceptable
- "gonna" vs "going to" - acceptable

**Unacceptable Errors:**
- Wrong words: "cat" → "can"
- Missing words: entire words omitted
- Extra words: hallucinated content
- Name errors: "Sarah" → "Sara" (may be acceptable)

---

### Issue: Response Times Slow (>3s)

**Possible Causes:**
1. Network latency
2. Database connection issues
3. Connection pool not initialized
4. High server load

**Solutions:**
1. Check network connectivity
2. Verify WorkOS database accessible
3. Restart bot to reinitialize connection pool
4. Check system resources (CPU, memory)
5. Review bot logs for slow query warnings

**Debugging:**
```bash
# Check bot logs
tail -f telegram_bot.log | grep -E "Response time|slow|WARNING"

# Monitor connection pool
grep "Pool stats" telegram_bot.log
```

---

### Issue: Screenshots Not Processing

**Possible Causes:**
1. File size too large
2. Unsupported image format
3. Caption not being captured
4. Photo handler not registered

**Solutions:**
1. Verify photo handler exists in telegram_bot.py
2. Check file size limits
3. Test with different image formats (JPEG, PNG)
4. Verify caption is being extracted
5. Check bot logs for errors

**Test with:**
```python
# In telegram_bot.py, verify handler registered:
self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
```

---

## Reporting Results

### Pass Criteria

**Full Approval:**
- All 6 acceptance criteria PASS
- No critical issues found
- All tests completed

**Conditional Approval:**
- 5-6 acceptance criteria PASS
- Minor non-blocking issues documented
- Issues have clear remediation path
- Voice accuracy ≥95% (non-negotiable)
- Response times <3s (non-negotiable)

**Rejection:**
- Voice accuracy <95%
- Response times consistently >3s
- Quick actions broken
- Multiple critical issues

### Documentation

Fill in checklist completely:
- [ ] All checkboxes marked
- [ ] All measurements recorded
- [ ] Issues documented with details
- [ ] Overall results calculated
- [ ] Tester signature and date

### Submitting Results

1. **Complete Checklist:**
   - Mark all pass/fail boxes
   - Fill in all measurements
   - Document all issues

2. **Generate Summary:**
   - Count total tests: 35
   - Count passed tests: _____
   - Calculate pass rate: _____%

3. **Create Issue Tickets:**
   - For each FAIL or critical issue
   - Include steps to reproduce
   - Include expected vs actual results

4. **Update Build Progress:**
   ```bash
   # Document completion
   echo "UAT COMPLETED: [DATE]" >> .auto-claude/specs/054-enhanced-telegram-bot-experience/build-progress.txt
   echo "Results: [PASS_COUNT]/35 tests passed" >> ...
   echo "Status: [APPROVED/REJECTED/CONDITIONAL]" >> ...
   ```

---

## Next Steps After UAT

### If APPROVED:
1. ✅ Mark subtask-5-3 as completed
2. ✅ Update implementation_plan.json status
3. ✅ Commit UAT results
4. ✅ Proceed to QA signoff
5. ✅ Merge feature to main branch

### If CONDITIONALLY APPROVED:
1. ⚠️ Document conditions for approval
2. ⚠️ Create remediation tasks
3. ⚠️ Schedule follow-up testing
4. ⚠️ Proceed with non-blocking deployment

### If REJECTED:
1. ❌ Document all failures
2. ❌ Create bug fix tasks
3. ❌ Fix critical issues
4. ❌ Re-run UAT from Phase 1

---

## Appendix: Quick Reference

### Acceptance Criteria Checklist

```
[ ] AC1: Inline keyboard buttons for common task actions
[ ] AC2: Voice message transcription accuracy > 95%
[ ] AC3: Screenshots can be analyzed and context extracted
[ ] AC4: Quick action buttons: brain dump, complete task, log energy
[ ] AC5: Response time < 3 seconds for common operations
[ ] AC6: Rich formatting in bot responses
```

### Performance Targets

```
Task query:        < 2 seconds  (expected: ~0.6-0.9s)
Brain dump:        < 3 seconds  (expected: ~0.8-1.2s)
Energy log:        < 1 second   (expected: ~0.2-0.4s)
Voice (10s audio): < 5 seconds  (expected: ~2-4s)
Task complete:     < 2 seconds  (expected: ~0.5-1.0s)
```

### Voice Accuracy Targets

```
Clear speech:    ≥ 95% accuracy
Technical terms: ≥ 95% accuracy
With noise:      ≥ 90% accuracy
Average:         ≥ 95% accuracy (REQUIRED)
```

---

**Document Version:** 1.0
**Last Updated:** 2026-01-26
**Ready for Execution:** ✅ YES
