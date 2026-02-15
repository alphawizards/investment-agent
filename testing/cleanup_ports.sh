#!/bin/bash

################################################################################
# Port Cleanup Utility
# =====================
# Kills processes running on backend and frontend ports
#
# Usage: ./cleanup_ports.sh
################################################################################

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

BACKEND_PORT=8000
FRONTEND_PORT=3000

echo -e "${YELLOW}🧹 Cleaning up ports $BACKEND_PORT and $FRONTEND_PORT...${NC}"
echo ""

# Function to kill process on port
kill_port() {
    local port=$1
    local pids=$(lsof -ti:$port 2>/dev/null)
    
    if [ -z "$pids" ]; then
        echo -e "${GREEN}✅ Port $port is already free${NC}"
        return 0
    fi
    
    echo -e "${YELLOW}⚠️  Found process(es) on port $port: $pids${NC}"
    
    # Try graceful kill first
    echo "   Attempting graceful shutdown..."
    echo "$pids" | xargs kill 2>/dev/null
    sleep 2
    
    # Check if still running
    pids=$(lsof -ti:$port 2>/dev/null)
    if [ -z "$pids" ]; then
        echo -e "${GREEN}✅ Port $port cleaned successfully${NC}"
        return 0
    fi
    
    # Force kill if still running
    echo "   Process still running, forcing kill..."
    echo "$pids" | xargs kill -9 2>/dev/null
    sleep 1
    
    # Final check
    pids=$(lsof -ti:$port 2>/dev/null)
    if [ -z "$pids" ]; then
        echo -e "${GREEN}✅ Port $port cleaned successfully (forced)${NC}"
        return 0
    else
        echo -e "${RED}❌ Failed to clean port $port${NC}"
        return 1
    fi
}

# Clean backend port
kill_port $BACKEND_PORT

echo ""

# Clean frontend port
kill_port $FRONTEND_PORT

echo ""
echo -e "${GREEN}🎉 Port cleanup complete!${NC}"
