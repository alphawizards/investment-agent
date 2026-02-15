# AI Agent Prompt: E2E Testing Execution

**Task:** Execute comprehensive end-to-end testing for the Potential Parakeet trading platform  
**Platform:** Quantitative trading platform (React + FastAPI + SQLite)  
**Repository:** alphawizards/potential-parakeet  
**Expected Duration:** 30-45 minutes  

---

## 🎯 Mission Objective

You are a **QA Test Engineer** tasked with executing the complete end-to-end testing suite for the Potential Parakeet trading platform. Your goal is to validate that the React frontend and FastAPI backend integrate correctly and that all critical user workflows function as expected.

**Success Criteria:** All E2E tests pass, HTML report generated, platform confirmed ready for production deployment.

---

## 📋 Prerequisites Checklist

Before starting, verify these conditions are met:

### Repository Access
- [ ] GitHub repository cloned: `alphawizards/potential-parakeet`
- [ ] Working directory: `/home/ubuntu/potential-parakeet`
- [ ] Git branch: `main` (or latest)

### Environment Setup
- [ ] Python 3.11+ installed
- [ ] Node.js 22+ installed
- [ ] Virtual environment exists: `venv/`
- [ ] Backend dependencies installed: `pip install -r requirements.txt`
- [ ] Frontend dependencies installed: `cd dashboard && npm install`

### Build Status
- [ ] Frontend production build exists: `dashboard/dist/`
- [ ] Database initialized: `data/trades.db` exists
- [ ] Playwright installed: `npx playwright install`

### Port Availability
- [ ] Port 8000 free (backend)
- [ ] Port 3000 free (frontend)

---

## 🚀 Execution Steps

### Step 1: Navigate to Repository

```bash
cd /home/ubuntu/potential-parakeet
```

### Step 2: Verify Testing Scripts Exist

Check that the E2E testing suite is available:

```bash
ls -la testing/
# Expected files:
# - run_e2e_tests.sh
# - cleanup_ports.sh
# - E2E_TESTING_README.md
# - E2E_TESTING_GUIDE.md
```

### Step 3: Review Documentation (Optional)

If you need context, read:
- `testing/E2E_TESTING_README.md` - Quick start guide
- `testing/E2E_TESTING_GUIDE.md` - Comprehensive documentation
- `docs/FINAL_DEPLOYMENT_REPORT.md` - Current platform status

### Step 4: Execute E2E Test Suite

Run the automated test script:

```bash
./testing/run_e2e_tests.sh
```

**What This Script Does:**
1. ✅ Pre-flight checks (venv, build, database)
2. ✅ Starts backend server (port 8000)
3. ✅ Starts frontend server (port 3000)
4. ✅ Verifies service health
5. ✅ Runs Playwright E2E tests
6. ✅ Generates HTML report
7. ✅ Collects logs and artifacts
8. ✅ Cleans up servers automatically

### Step 5: Monitor Execution

Watch for these status indicators:

**✅ Success Indicators:**
- Green checkmarks (✅) throughout execution
- "All E2E tests passed! ✨"
- "Platform is ready for production deployment"
- Exit code: 0

**❌ Failure Indicators:**
- Red X marks (❌) during execution
- "Some E2E tests failed"
- "Review the report and fix issues"
- Exit code: 1

### Step 6: Review Test Report

After execution completes, examine the HTML report:

```bash
# Report location
ls -la playwright-report/index.html

# Open report (if browser available)
npx playwright show-report

# Or view file path
echo "file://$(pwd)/playwright-report/index.html"
```

**What to Check:**
- Total tests run
- Pass/fail counts
- Failed test details (if any)
- Screenshots of failures
- Execution traces

### Step 7: Analyze Logs (If Tests Failed)

If tests fail, check logs for details:

```bash
# Backend logs
tail -50 logs/backend-e2e.log

# Frontend logs
tail -50 logs/frontend-e2e.log

# Check for errors
grep -i error logs/*.log
```

### Step 8: Collect Artifacts

Test artifacts are automatically saved:

```bash
# Find latest artifacts directory
ls -dt test-artifacts-* | head -1

# View test summary
cat test-artifacts-*/test-summary.txt
```

---

## 🔍 Expected Test Results

### Successful Run Output

```
================================================================================
Potential Parakeet E2E Test Suite
================================================================================
Start Time: 2026-01-03 10:00:00

================================================================================
Step 1: Pre-flight Checks
================================================================================
✅ Pre-flight checks complete

================================================================================
Step 2: Starting Backend Server
================================================================================
ℹ️  Starting FastAPI backend on port 8000...
✅ Backend API is ready!
✅ Backend health check: healthy

================================================================================
Step 3: Starting Frontend Server
================================================================================
ℹ️  Starting frontend server on port 3000...
✅ Frontend Server is ready!
✅ Frontend is serving production build

================================================================================
Step 4: Verifying Services
================================================================================
✅ ✓ /health endpoint responding
✅ ✓ /api/trades/ endpoint responding
✅ ✓ Frontend serving index.html

================================================================================
Step 5: Running Playwright E2E Tests
================================================================================
Running 30 tests using 3 workers

  ✓ dashboard.spec.ts:5:1 › Dashboard loads successfully (2.1s)
  ✓ dashboard.spec.ts:12:1 › Dashboard displays metrics (1.8s)
  ✓ trades.spec.ts:5:1 › Trade list loads (1.5s)
  ... (27 more tests)

  30 passed (45.2s)

✅ All E2E tests passed! ✨

================================================================================
E2E Test Execution Complete
================================================================================
Test Status: PASSED
✅ 🎉 All tests passed! Platform is ready for production deployment.
```

### Test Metrics

| Metric | Expected Value |
|--------|----------------|
| **Total Tests** | ~30 |
| **Pass Rate** | 100% |
| **Execution Time** | < 5 minutes |
| **Backend Startup** | < 10 seconds |
| **Frontend Startup** | < 5 seconds |
| **Page Load Time** | < 3 seconds |
| **API Response Time** | < 500ms |

---

## 🐛 Troubleshooting Guide

### Issue 1: Ports Already in Use

**Error:** `Port 8000 is already in use`

**Solution:**
```bash
./testing/cleanup_ports.sh
# Then retry: ./testing/run_e2e_tests.sh
```

### Issue 2: Frontend Build Missing

**Error:** `Frontend build not found`

**Solution:**
```bash
cd dashboard
npm install
npm run build
cd ..
# Then retry: ./testing/run_e2e_tests.sh
```

### Issue 3: Backend Won't Start

**Error:** `Backend failed to start`

**Solution:**
```bash
# Check logs
tail -50 logs/backend-e2e.log

# Verify dependencies
source venv/bin/activate
pip install -r requirements.txt
deactivate

# Then retry
./testing/run_e2e_tests.sh
```

### Issue 4: Database Not Initialized

**Error:** `Database not found`

**Solution:**
```bash
source venv/bin/activate
python backend/seed_data.py
deactivate
# Then retry: ./testing/run_e2e_tests.sh
```

### Issue 5: Playwright Browsers Missing

**Error:** `Executable doesn't exist`

**Solution:**
```bash
npx playwright install
# Then retry: ./testing/run_e2e_tests.sh
```

### Issue 6: Tests Timing Out

**Error:** `Test timeout of 30000ms exceeded`

**Solution:**
- Check if backend is responding slowly
- Verify database has data
- Check system resources
- Increase timeout in `playwright.config.js` if needed

---

## 📊 Deliverables

After completing E2E testing, provide:

### 1. Test Execution Summary

```markdown
## E2E Test Execution Report

**Date:** [Execution Date]
**Duration:** [Total Time]
**Status:** [PASSED/FAILED]

### Results
- Total Tests: [Number]
- Passed: [Number]
- Failed: [Number]
- Pass Rate: [Percentage]

### Test Status: [PASSED/FAILED]
```

### 2. Test Report Location

```
File: playwright-report/index.html
URL: file:///home/ubuntu/potential-parakeet/playwright-report/index.html
```

### 3. Artifacts Location

```
Directory: test-artifacts-[timestamp]/
Contents:
- backend-e2e.log
- frontend-e2e.log
- playwright-report/
- test-summary.txt
```

### 4. Issues Found (If Any)

For each failed test:
- Test name
- Error message
- Screenshot (if available)
- Recommended fix

### 5. Final Recommendation

Based on test results:
- ✅ **PASS:** Platform ready for production deployment
- ❌ **FAIL:** Platform NOT ready - issues must be fixed first

---

## 🎯 Success Criteria

### Test Execution Successful When:

- ✅ All 30 E2E tests pass (100% pass rate)
- ✅ No console errors in browser
- ✅ All API endpoints return 200 status
- ✅ Page load times < 3 seconds
- ✅ Backend and frontend integrate correctly
- ✅ HTML report generated successfully
- ✅ No critical issues found

### Platform Ready for Deployment When:

- ✅ Test Status: PASSED
- ✅ Pass Rate: 100%
- ✅ All critical user flows working
- ✅ No blockers identified
- ✅ Performance metrics met

---

## 📝 Reporting Template

Use this template for your final report:

```markdown
# E2E Testing Execution Report

**Platform:** Potential Parakeet Trading Platform
**Date:** [Date]
**Tester:** AI QA Agent
**Duration:** [Duration]

---

## Executive Summary

[Brief overview of testing execution and results]

---

## Test Results

| Metric | Result |
|--------|--------|
| Total Tests | [Number] |
| Passed | [Number] |
| Failed | [Number] |
| Skipped | [Number] |
| Pass Rate | [Percentage] |
| Execution Time | [Time] |

---

## Test Status: [PASSED/FAILED]

[Detailed explanation of results]

---

## Issues Found

[List any issues, or state "No issues found"]

---

## Artifacts

- Test Report: `playwright-report/index.html`
- Backend Log: `logs/backend-e2e.log`
- Frontend Log: `logs/frontend-e2e.log`
- Artifacts: `test-artifacts-[timestamp]/`

---

## Recommendation

[READY FOR DEPLOYMENT / NOT READY - ISSUES MUST BE FIXED]

---

## Next Steps

[Recommended actions based on results]
```

---

## 🚨 Important Notes

### Do NOT:
- ❌ Skip pre-flight checks
- ❌ Run tests without proper setup
- ❌ Ignore failed tests
- ❌ Deploy if tests fail
- ❌ Modify test scripts without understanding them

### DO:
- ✅ Follow steps in order
- ✅ Read error messages carefully
- ✅ Check logs when issues occur
- ✅ Document all findings
- ✅ Provide clear recommendations

---

## 🔗 Reference Documentation

Available in the repository:

- **E2E Testing Guide:** `testing/E2E_TESTING_GUIDE.md`
- **Quick Start:** `testing/E2E_TESTING_README.md`
- **Deployment Report:** `docs/FINAL_DEPLOYMENT_REPORT.md`
- **Frontend Fixes:** `docs/FRONTEND_FIX_GUIDE.md`
- **Build Report:** `docs/BUILD_SUCCESS_REPORT.md`
- **Dashboard Testing:** `docs/DASHBOARD_TESTING_REPORT.md`

---

## 🎓 Context: Platform Status

### Current State (as of last testing):
- ✅ Backend API: Fully operational
- ✅ Frontend Build: Production ready
- ✅ Database: Initialized with 100 trades
- ✅ Static Dashboards: Working (OLMAR, Quant2, etc.)
- ✅ Test Pass Rate: 96% (previous run)
- ✅ Status: Ready for staging deployment

### What E2E Tests Validate:
- Frontend → Backend API integration
- Data fetching and display
- User workflows (dashboard, trades, strategies)
- Error handling
- Performance benchmarks

---

## ✅ Final Checklist

Before reporting completion:

- [ ] E2E test script executed successfully
- [ ] Test report generated and reviewed
- [ ] All logs collected
- [ ] Artifacts saved
- [ ] Issues documented (if any)
- [ ] Final recommendation provided
- [ ] Report delivered to user

---

## 🎉 Expected Outcome

If all goes well, you should report:

```
✅ E2E Testing Complete

Test Status: PASSED
Pass Rate: 100% (30/30 tests)
Execution Time: ~5 minutes

Recommendation: READY FOR PRODUCTION DEPLOYMENT

The Potential Parakeet trading platform has passed comprehensive
end-to-end testing. All critical user workflows function correctly,
frontend-backend integration is validated, and the platform is
ready for production deployment.
```

---

**Good luck with the testing! 🚀**

---

## 📞 Support

If you encounter issues not covered in this prompt:
1. Check `testing/E2E_TESTING_GUIDE.md` for detailed troubleshooting
2. Review logs in `logs/` directory
3. Examine test report for specific failure details
4. Run in debug mode: `npx playwright test --debug`

---

**End of Prompt**
