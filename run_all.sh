#!/bin/bash

# ==============================================================================
#                 LiverLink Launcher — Connected Fullstack Server
# ==============================================================================
# This script starts both the Google ADK Agent Server and the FastAPI Web
# Proxy Server concurrently, handles clean teardown, and handles log routing.
# ==============================================================================

# Exit on any unexpected error
set -e

# Setup colors for elegant terminal outputs
GREEN="\033[0;32m"
CYAN="\033[0;36m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
BOLD="\033[1m"
NC="\033[0m" # No Color

# Determine project base directory
BASE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$BASE_DIR"

echo -e "${CYAN}${BOLD}"
echo "======================================================================"
echo "                   L I V E R L I N K   L A U N C H E R                "
echo "======================================================================"
echo -e "${NC}"

# Verification 1: Verify virtual environment
VENV_PATH="$BASE_DIR/.venv"
if [ ! -d "$VENV_PATH" ]; then
    echo -e "${RED}[ERROR] Virtual environment (.venv) not found at base path: $BASE_DIR${NC}"
    echo -e "Please configure python and create a virtual environment first."
    exit 1
fi
PYTHON_EXEC="$VENV_PATH/bin/python"
ADK_EXEC="$VENV_PATH/bin/adk"

# Verification 2: Verify .env exists
if [ ! -f "$BASE_DIR/.env" ]; then
    echo -e "${YELLOW}[WARNING] .env file not found. Copying from .env.example...${NC}"
    if [ -f "$BASE_DIR/.env.example" ]; then
        cp "$BASE_DIR/.env.example" "$BASE_DIR/.env"
        echo -e "${GREEN}Created default .env. Please fill in your API keys!${NC}"
    else
        echo -e "${RED}[ERROR] Neither .env nor .env.example were found at $BASE_DIR.${NC}"
        exit 1
    fi
fi

# Ensure cleanup of background tasks on Ctrl+C / Exit
cleanup() {
    echo -e "\n${YELLOW}Stopping background servers and clean exiting...${NC}"
    
    # Terminate background process groups gently
    if [ ! -z "$ADK_PID" ]; then
        echo -e "Shutting down ADK Server (PID: $ADK_PID)..."
        kill -15 "$ADK_PID" 2>/dev/null || true
    fi
    
    if [ ! -z "$PROXY_PID" ]; then
        echo -e "Shutting down FastAPI Proxy Server (PID: $PROXY_PID)..."
        kill -15 "$PROXY_PID" 2>/dev/null || true
    fi
    
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# Step 1: Start the Google ADK Agent Server
echo -e "${GREEN}[1/2] Starting Google ADK Agent Server on Port 8000...${NC}"
cd "$BASE_DIR/backend/agents"
"$ADK_EXEC" web > "$BASE_DIR/adk_server.log" 2>&1 &
ADK_PID=$!
cd "$BASE_DIR"

# Step 2: Start the FastAPI Proxy Web Server
echo -e "${GREEN}[2/2] Starting FastAPI Proxy & Web Server on Port 8080...${NC}"
"$PYTHON_EXEC" "$BASE_DIR/backend/proxy_server.py" > "$BASE_DIR/proxy_server.log" 2>&1 &
PROXY_PID=$!

# Give servers 2 seconds to initialize
sleep 2

# Check if processes are still running
if ! kill -0 "$ADK_PID" 2>/dev/null; then
    echo -e "${RED}[ERROR] ADK Server failed to start. Review logs at: $BASE_DIR/adk_server.log${NC}"
    exit 1
fi

if ! kill -0 "$PROXY_PID" 2>/dev/null; then
    echo -e "${RED}[ERROR] Web Proxy Server failed to start. Review logs at: $BASE_DIR/proxy_server.log${NC}"
    exit 1
fi

echo -e "\n${GREEN}${BOLD}🚀 All servers are running successfully!${NC}"
echo -e "----------------------------------------------------------------------"
echo -e "  💻 ${BOLD}Interactive Portal UI${NC}     : ${CYAN}http://127.0.0.1:8080/${NC}"
echo -e "  🔬 ${BOLD}AI Lab Report Scanner${NC}    : ${CYAN}http://127.0.0.1:8080/scanner${NC}"
echo -e "  💬 ${BOLD}ADK Agent Dev Chat UI${NC}    : ${CYAN}http://127.0.0.1:8000/${NC}"
echo -e "----------------------------------------------------------------------"
echo -e "  📜 ${BOLD}ADK Log Output File${NC}      : $BASE_DIR/adk_server.log"
echo -e "  📜 ${BOLD}Proxy Log Output File${NC}    : $BASE_DIR/proxy_server.log"
echo -e "----------------------------------------------------------------------"
echo -e "${YELLOW}Keep this window open. Press Ctrl+C at any time to safely shut down both servers.${NC}\n"

# Keep script active to print ongoing status/logs if desired, or simple keep-alive
while kill -0 "$ADK_PID" 2>/dev/null && kill -0 "$PROXY_PID" 2>/dev/null; do
    sleep 1
done
