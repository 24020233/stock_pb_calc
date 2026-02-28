@echo off
chcp 65001 >nul
title 蓝胖子自动选股系统 - 启动脚本

:: 获取脚本所在目录
set "SCRIPT_DIR=%~dp0"
set "BACKEND_DIR=%SCRIPT_DIR%web_rebuild\backend"
set "FRONTEND_DIR=%SCRIPT_DIR%web_rebuild\frontend"

echo ========================================
echo    蓝胖子自动选股系统 - 启动中...
echo ========================================

:: 检查 .env 文件
if not exist "%SCRIPT_DIR%web_rebuild\.env" (
    echo [警告] .env 文件不存在，请先配置环境变量
    echo 可以复制 .env.example 为 .env 并修改配置
)

:: 启动后端
echo [1/2] 启动后端服务...
start "蓝胖子后端 - FastAPI" cmd /k "cd /d %BACKEND_DIR% && python main.py"
echo 后端服务启动成功 (http://localhost:8002)
echo API 文档: http://localhost:8002/docs

:: 等待后端启动
timeout /t 2 /nobreak >nul

:: 启动前端
echo [2/2] 启动前端服务...
start "蓝胖子前端 - React" cmd /k "cd /d %FRONTEND_DIR% && npm run dev"
echo 前端服务启动成功 (http://localhost:3000)

echo.
echo ========================================
echo    启动完成！
echo ========================================
echo 后端地址: http://localhost:8002
echo API文档:  http://localhost:8002/docs
echo 前端地址: http://localhost:3000
echo.
echo 提示: 使用 stop.bat 停止服务
echo.
pause