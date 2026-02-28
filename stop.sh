#!/bin/bash
# 蓝胖子自动选股系统 - 一键停止脚本 (macOS版)

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
BACKEND_PID=$(lsof -i :$BACKEND_PORT -t 2>/dev/null)
if [ -n "$BACKEND_PID" ]; then
    kill -9 $BACKEND_PID 2>/dev/null
    echo -e "${GREEN}后端服务已停止${NC}"
else
    echo -e "${YELLOW}后端服务未运行${NC}"
fi

# 停止前端服务
echo -e "${YELLOW}[2/2] 停止前端服务 (端口 $FRONTEND_PORT)...${NC}"
FRONTEND_PID=$(lsof -i :$FRONTEND_PORT -t 2>/dev/null)
if [ -n "$FRONTEND_PID" ]; then
    kill -9 $FRONTEND_PID 2>/dev/null
    echo -e "${GREEN}前端服务已停止${NC}"
else
    echo -e "${YELLOW}前端服务未运行${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   所有服务已停止${NC}"
echo -e "${GREEN}========================================${NC}"