@echo off
chcp 65001 >nul
title 蓝胖子自动选股系统 - 停止脚本

echo ========================================
echo    蓝胖子自动选股系统 - 停止中...
echo ========================================

:: 停止后端服务 (端口 8002)
echo [1/2] 停止后端服务 (端口 8002)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8002.*LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
    echo 后端服务已停止
)
if not exist "%%a" echo 后端服务未运行

:: 停止前端服务 (端口 3000)
echo [2/2] 停止前端服务 (端口 3000)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000.*LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
    echo 前端服务已停止
)
if not exist "%%a" echo 前端服务未运行

:: 关闭启动脚本打开的窗口
echo 清理残留窗口...
taskkill /FI "WINDOWTITLE eq 蓝胖子后端*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq 蓝胖子前端*" /F >nul 2>&1

echo.
echo ========================================
echo    所有服务已停止
echo ========================================
pause