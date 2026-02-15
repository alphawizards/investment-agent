# E2E Testing Package

**Complete end-to-end testing solution for Potential Parakeet Trading Platform**

---

## 📦 Package Contents

This E2E testing package includes:

1. **`run_e2e_tests.sh`** - Main test execution script
2. **`E2E_TESTING_GUIDE.md`** - Comprehensive testing documentation
3. **`cleanup_ports.sh`** - Port cleanup utility

---

## 🚀 Quick Start

### One-Line Execution

```bash
cd /home/ubuntu/potential-parakeet && ./testing/run_e2e_tests.sh
```

That's all you need! The script handles everything automatically.

---

## 📋 What the Script Does

1. **Pre-flight Checks** - Verifies environment setup
2. **Start Backend Server** - Launches FastAPI on port 8000
3. **Start Frontend Server** - Serves React build on port 3000
4. **Verify Services** - Tests health endpoints
5. **Run Playwright Tests** - Executes E2E test suite
6. **Generate Report** - Creates HTML test report
7. **Cleanup** - Stops servers gracefully

---

## ✅ Success Criteria

When all tests pass:
- ✅ 30/30 tests passed
- ✅ Test Status: PASSED
- ✅ Platform ready for production

---

## 🛠️ Utility Scripts

### Cleanup Ports

If ports are stuck in use:

```bash
./testing/cleanup_ports.sh
```

---

## 📁 Output Files

After running tests:

- `playwright-report/index.html` - Test report
- `logs/backend-e2e.log` - Backend logs
- `logs/frontend-e2e.log` - Frontend logs

---

## 🐛 Troubleshooting

### Ports Already in Use
```bash
./testing/cleanup_ports.sh
```

### Backend Won't Start
```bash
tail -f logs/backend-e2e.log
```

### Frontend Build Missing
```bash
cd dashboard && npm run build
```

---

**Happy Testing!** 🧪✨
