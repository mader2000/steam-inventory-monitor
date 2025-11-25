@echo off
chcp 65001 >nul
echo ====================================
echo Steam库存监控程序启动脚本
echo ====================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到Python,请先安装Python 3.6+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [提示] Python环境检测通过
echo.

REM 检查依赖是否安装
echo [检查] 正在检查依赖包...
pip show requests >nul 2>&1
if %errorlevel% neq 0 (
    echo [安装] 正在安装依赖包...
    pip install -r requirements.txt
)

echo.
echo [启动] 开始运行监控程序...
echo [提示] 按 Ctrl+C 可停止程序
echo.

python steam_inventory_monitor.py

pause
