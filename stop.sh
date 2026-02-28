#!/bin/bash
# 蓝胖子自动选股系统 - 一键停止脚本

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   蓝胖子自动选股系统 - 停止中...${NC}"
echo -e "${GREEN}========================================${NC}"

# 后端端口
BACKEND_PORT=8002
# 前端端口
FRONTEND_PORT=3000

# 停止后端服务
echo -e "${YELLOW}[1/2] 停止后端服务 (端口 $BACKEND_PORT)...${NC}"
BACKEND_PID=$(netstat -ano | grep ":$BACKEND_PORT" | grep "LISTENING" | awk '{print $NF}' | head -1)
if [ -n "$BACKEND_PID" ]; then
    taskkill /F /PID $BACKEND_PID > /dev/null 2>&1
    echo -e "${GREEN}后端服务已停止${NC}"
else
    echo -e "${YELLOW}后端服务未运行${NC}"
fi

# 停止前端服务
echo -e "${YELLOW}[2/2] 停止前端服务 (端口 $FRONTEND_PORT)...${NC}"
FRONTEND_PID=$(netstat -ano | grep ":$FRONTEND_PORT" | grep "LISTENING" | awk '{print $NF}' | head -1)
if [ -n "$FRONTEND_PID" ]; then
    taskkill /F /PID $FRONTEND_PID > /dev/null 2>&1
    echo -e "${GREEN}前端服务已停止${NC}"
else
    echo -e "${YELLOW}前端服务未运行${NC}"
fi

# 清理可能的残留 node 进程 (Vite 开发服务器)
echo -e "${YELLOW}清理残留进程...${NC}"
taskkill /F /IM node.exe /FI "WINDOWTITLE eq *蓝胖子前端*" > /dev/null 2>&1
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *蓝胖子后端*" > /dev/null 2>&1

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   所有服务已停止${NC}"
echo -e "${GREEN}========================================${NC}"