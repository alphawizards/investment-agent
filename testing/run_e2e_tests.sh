#!/bin/bash

################################################################################
# E2E Test Execution Script
# ==========================
# Comprehensive end-to-end testing for Potential Parakeet Trading Platform
#
# This script:
# 1. Starts the FastAPI backend server
# 2. Serves the production React frontend
# 3. Runs Playwright E2E tests
# 4. Generates HTML test report
# 5. Cleans up processes on exit
#
# Usage: ./run_e2e_tests.sh
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_PORT=8000
FRONTEND_PORT=3000
BACKEND_LOG="$PROJECT_ROOT/logs/backend-e2e.log"
FRONTEND_LOG="$PROJECT_ROOT/logs/frontend-e2e.log"
BACKEND_PID_FILE="$PROJECT_ROOT/logs/backend.pid"
FRONTEND_PID_FILE="$PROJECT_ROOT/logs/frontend.pid"
TEST_REPORT_DIR="$PROJECT_ROOT/playwright-report"

# Create logs directory
mkdir -p "$PROJECT_ROOT/logs"

################################################################################
# Helper Functions
################################################################################

print_header() {
    echo -e "${CYAN}"
    echo "================================================================================"
    echo "$1"
    echo "================================================================================"
    echo -e "${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Cleanup function - called on exit
cleanup() {
    print_header "Cleaning Up"
    
    # Kill backend if running
    if [ -f "$BACKEND_PID_FILE" ]; then
        BACKEND_PID=$(cat "$BACKEND_PID_FILE")
        if ps -p $BACKEND_PID > /dev/null 2>&1; then
            print_info "Stopping backend server (PID: $BACKEND_PID)..."
            kill $BACKEND_PID 2>/dev/null || true
            sleep 2
            if ps -p $BACKEND_PID > /dev/null 2>&1; then
                kill -9 $BACKEND_PID 2>/dev/null || true
            fi
        fi
        rm -f "$BACKEND_PID_FILE"
    fi
    
    # Kill frontend if running
    if [ -f "$FRONTEND_PID_FILE" ]; then
        FRONTEND_PID=$(cat "$FRONTEND_PID_FILE")
        if ps -p $FRONTEND_PID > /dev/null 2>&1; then
            print_info "Stopping frontend server (PID: $FRONTEND_PID)..."
            kill $FRONTEND_PID 2>/dev/null || true
            sleep 2
            if ps -p $FRONTEND_PID > /dev/null 2>&1; then
                kill -9 $FRONTEND_PID 2>/dev/null || true
            fi
        fi
        rm -f "$FRONTEND_PID_FILE"
    fi
    
    # Kill any remaining processes on the ports
    print_info "Cleaning up any remaining processes on ports $BACKEND_PORT and $FRONTEND_PORT..."
    lsof -ti:$BACKEND_PORT | xargs kill -9 2>/dev/null || true
    lsof -ti:$FRONTEND_PORT | xargs kill -9 2>/dev/null || true
    
    print_success "Cleanup complete"
}

# Set trap to cleanup on exit
trap cleanup EXIT INT TERM

# Check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Wait for service to be ready
wait_for_service() {
    local url=$1
    local service_name=$2
    local max_attempts=30
    local attempt=0
    
    print_info "Waiting for $service_name to be ready..."
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            print_success "$service_name is ready!"
            return 0
        fi
        
        attempt=$((attempt + 1))
        echo -n "."
        sleep 1
    done
    
    echo ""
    print_error "$service_name failed to start within $max_attempts seconds"
    return 1
}

################################################################################
# Main Execution
################################################################################

print_header "Potential Parakeet E2E Test Suite"
echo "Start Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Navigate to project root
cd "$PROJECT_ROOT"

################################################################################
# Step 1: Pre-flight Checks
################################################################################

print_header "Step 1: Pre-flight Checks"

if [ ! -d "venv" ]; then
    print_error "Virtual environment not found. Creating..."
    python3.11 -m venv venv
fi

if [ ! -d "dashboard/dist" ]; then
    print_error "Frontend build not found. Please run 'npm run build' first."
    exit 1
fi

if [ ! -f "data/trades.db" ]; then
    print_warning "Database not found. Running seed script..."
    source venv/bin/activate
    python backend/seed_data.py
    deactivate
fi

print_success "Pre-flight checks complete"
echo ""

################################################################################
# Step 2: Start Backend Server
################################################################################

print_header "Step 2: Starting Backend Server"

if check_port $BACKEND_PORT; then
    print_warning "Port $BACKEND_PORT is already in use. Killing existing process..."
    lsof -ti:$BACKEND_PORT | xargs kill -9 2>/dev/null || true
    sleep 2
fi

print_info "Starting FastAPI backend on port $BACKEND_PORT..."
source venv/bin/activate
nohup python -m backend.main > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > "$BACKEND_PID_FILE"
deactivate

print_info "Backend PID: $BACKEND_PID"

if ! wait_for_service "http://localhost:$BACKEND_PORT/health" "Backend API"; then
    print_error "Backend failed to start. Check logs at $BACKEND_LOG"
    exit 1
fi

print_success "Backend health check: healthy"
echo ""

################################################################################
# Step 3: Start Frontend Server
################################################################################

print_header "Step 3: Starting Frontend Server"

if check_port $FRONTEND_PORT; then
    print_warning "Port $FRONTEND_PORT is already in use. Killing existing process..."
    lsof -ti:$FRONTEND_PORT | xargs kill -9 2>/dev/null || true
    sleep 2
fi

print_info "Starting frontend server on port $FRONTEND_PORT..."
cd "$PROJECT_ROOT/dashboard"
nohup npx serve dist -p $FRONTEND_PORT > "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > "$FRONTEND_PID_FILE"

print_info "Frontend PID: $FRONTEND_PID"

if ! wait_for_service "http://localhost:$FRONTEND_PORT" "Frontend Server"; then
    print_error "Frontend failed to start. Check logs at $FRONTEND_LOG"
    exit 1
fi

print_success "Frontend is serving production build"
echo ""

################################################################################
# Step 4: Run Playwright E2E Tests
################################################################################

print_header "Step 4: Running Playwright E2E Tests"

cd "$PROJECT_ROOT"

export BASE_URL="http://localhost:$FRONTEND_PORT"
export API_URL="http://localhost:$BACKEND_PORT"

print_info "Test Configuration:"
print_info "  Frontend URL: $BASE_URL"
print_info "  Backend URL: $API_URL"
echo ""

if npx playwright test --reporter=html,list; then
    print_success "All E2E tests passed! ✨"
    TEST_STATUS="PASSED"
    EXIT_CODE=0
else
    print_error "Some E2E tests failed. Check the report for details."
    TEST_STATUS="FAILED"
    EXIT_CODE=1
fi

echo ""

################################################################################
# Final Summary
################################################################################

print_header "E2E Test Execution Complete"

echo "End Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
echo "Summary:"
echo "  Test Status: $TEST_STATUS"
echo "  Test Report: file://$TEST_REPORT_DIR/index.html"
echo ""

if [ $EXIT_CODE -eq 0 ]; then
    print_success "🎉 All tests passed! Platform is ready for production deployment."
else
    print_error "⚠️  Some tests failed. Review the report and fix issues before deploying."
fi

exit $EXIT_CODE
