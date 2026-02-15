# E2E Testing Guide

**Platform:** Potential Parakeet Trading Platform  
**Test Type:** End-to-End (E2E) Integration Testing  
**Framework:** Playwright  

---

## 📋 Overview

This guide provides complete instructions for running end-to-end tests on the Potential Parakeet trading platform. The E2E test suite validates the integration between the React frontend and FastAPI backend.

---

## 🎯 What Gets Tested

### Frontend → Backend Integration
- ✅ API connectivity
- ✅ Data fetching and display
- ✅ Error handling
- ✅ Loading states
- ✅ User interactions

### Critical User Flows
- ✅ Dashboard loading
- ✅ Trade list display
- ✅ Filtering and sorting
- ✅ Navigation between pages
- ✅ Strategy dashboards

### Data Integrity
- ✅ Backend data matches frontend display
- ✅ Real-time updates
- ✅ Calculation accuracy

---

## 🚀 Quick Start

### One-Command Execution

```bash
cd /home/ubuntu/potential-parakeet
./testing/run_e2e_tests.sh
```

---

## 📖 Detailed Usage

### Prerequisites

Before running tests, ensure:

1. **Backend dependencies installed:**
   ```bash
   cd /home/ubuntu/potential-parakeet
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Frontend built:**
   ```bash
   cd dashboard
   npm install
   npm run build
   ```

3. **Database initialized:**
   ```bash
   python backend/seed_data.py
   ```

4. **Playwright installed:**
   ```bash
   npx playwright install
   ```

### Running the Tests

#### Automated Script (Recommended)

```bash
./testing/run_e2e_tests.sh
```

This script will:
1. ✅ Perform pre-flight checks
2. ✅ Start backend server (port 8000)
3. ✅ Start frontend server (port 3000)
4. ✅ Verify both services are healthy
5. ✅ Run Playwright test suite
6. ✅ Generate HTML test report
7. ✅ Clean up processes on exit

#### Manual Execution

```bash
# Terminal 1: Start backend
cd /home/ubuntu/potential-parakeet
source venv/bin/activate
python -m backend.main

# Terminal 2: Start frontend
cd /home/ubuntu/potential-parakeet/dashboard
npx serve dist -p 3000

# Terminal 3: Run tests
cd /home/ubuntu/potential-parakeet
export BASE_URL="http://localhost:3000"
export API_URL="http://localhost:8000"
npx playwright test --reporter=html
```

---

## 📊 Understanding Test Results

### Test Report Location

After running tests, the HTML report is generated at:
```
/home/ubuntu/potential-parakeet/playwright-report/index.html
```

Open it in a browser:
```bash
npx playwright show-report
```

### Test Status Indicators

- ✅ **PASSED** - All tests successful
- ❌ **FAILED** - One or more tests failed
- ⏭️ **SKIPPED** - Test was skipped
- ⏱️ **TIMEOUT** - Test exceeded time limit

---

## 🛠️ Configuration

### Environment Variables

```bash
BASE_URL="http://localhost:3000"    # Frontend URL
API_URL="http://localhost:8000"     # Backend URL
```

### Playwright Configuration

Edit `playwright.config.js` to customize:

```javascript
export default {
  testDir: './tests/e2e',
  timeout: 30000,
  retries: 2,
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
}
```

---

## 🐛 Troubleshooting

### Common Issues

#### 1. Port Already in Use

**Solution:**
```bash
./testing/cleanup_ports.sh
```

#### 2. Backend Not Starting

**Solution:**
```bash
# Check backend logs
tail -f logs/backend-e2e.log

# Verify dependencies
source venv/bin/activate
pip install -r requirements.txt
```

#### 3. Frontend Not Building

**Solution:**
```bash
cd dashboard
npm install
npm run build
```

#### 4. Playwright Browsers Missing

**Solution:**
```bash
npx playwright install
```

---

## 📈 Performance Benchmarks

### Expected Test Duration

| Test Suite | Tests | Duration |
|------------|-------|----------|
| Smoke Tests | 5 | ~30s |
| Integration Tests | 15 | ~2min |
| User Flow Tests | 10 | ~3min |
| **Total** | **30** | **~5min** |

---

## 🎯 Success Criteria

### Definition of Done

E2E tests are considered successful when:

- ✅ All test cases pass (100% pass rate)
- ✅ No console errors in browser
- ✅ All API calls return 200 status
- ✅ Page load times < 3 seconds
- ✅ No visual regressions
- ✅ All user flows complete successfully

---

## 🎉 Conclusion

The E2E test suite provides comprehensive validation of the Potential Parakeet platform. Running these tests before deployment ensures:

- ✅ Frontend and backend integrate correctly
- ✅ All user workflows function as expected
- ✅ No regressions introduced
- ✅ Platform is production-ready

**Run the tests, review the report, fix any issues, and deploy with confidence!** 🚀
