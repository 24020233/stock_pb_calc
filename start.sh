#!/bin/bash
# 蓝胖子自动选股系统 - 一键启动脚本 (macOS版)

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/web_rebuild/backend"
FRONTEND_DIR="$SCRIPT_DIR/web_rebuild/frontend"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   蓝胖子自动选股系统 - 启动中...${NC}"
echo -e "${GREEN}========================================${NC}"

# 检查 .env 文件是否存在
if [ ! -f "$SCRIPT_DIR/web_rebuild/.env" ]; then
    echo -e "${YELLOW}[警告] .env 文件不存在，请先配置环境变量${NC}"
    echo -e "${YELLOW}可以复制 .env.example 为 .env 并修改配置${NC}"
fi

# 启动后端
echo -e "${YELLOW}[1/2] 启动后端服务...${NC}"

# 检查是否已在运行
if lsof -i :8002 -t &>/dev/null; then
    echo -e "${YELLOW}后端服务已在运行 (端口 8002)${NC}"
else
    cd "$BACKEND_DIR"
    # 在 macOS 上使用 osascript 在新终端窗口启动
    osascript -e "tell application \"Terminal\" to do script \"cd '$BACKEND_DIR' && python main.py\""
    echo -e "${GREEN}后端服务启动成功 (http://localhost:8002)${NC}"
    echo -e "${GREEN}API 文档: http://localhost:8002/docs${NC}"
fi

# 等待后端启动
sleep 2

# 启动前端
echo -e "${YELLOW}[2/2] 启动前端服务...${NC}"

# 检查是否已在运行
if lsof -i :3000 -t &>/dev/null; then
    echo -e "${YELLOW}前端服务已在运行 (端口 3000)${NC}"
else
    cd "$FRONTEND_DIR"
    # 在 macOS 上使用 osascript 在新终端窗口启动
    osascript -e "tell application \"Terminal\" to do script \"cd '$FRONTEND_DIR' && npm run dev\""
    echo -e "${GREEN}前端服务启动成功 (http://localhost:3000)${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   启动完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "后端地址: ${GREEN}http://localhost:8002${NC}"
echo -e "API文档:  ${GREEN}http://localhost:8002/docs${NC}"
echo -e "前端地址: ${GREEN}http://localhost:3000${NC}"
echo ""
echo -e "${YELLOW}提示: 使用 stop.sh 脚本停止服务${NC}"