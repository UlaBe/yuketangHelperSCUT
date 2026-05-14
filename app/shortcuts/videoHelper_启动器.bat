@echo off
REM 智能启动器 - 由小辉nuitkaGUI自动生成
REM 生成时间: 2025-08-30 23:30:41
REM 原始程序: videoHelper.exe

setlocal

REM 获取当前脚本所在目录
set "SCRIPT_DIR=%~dp0"

REM 设置程序路径（相对于脚本位置）
set "PROGRAM_PATH=%SCRIPT_DIR%..\videoHelper.exe"

REM 检查程序是否存在
if not exist "%PROGRAM_PATH%" (
    echo 错误: 找不到程序文件
    echo 路径: %PROGRAM_PATH%
    echo.
    echo 请确保程序文件存在于正确位置
    pause
    exit /b 1
)

REM 切换到程序所在目录
cd /d "%SCRIPT_DIR%.."

REM 启动程序
echo 正在启动: videoHelper.exe
"%PROGRAM_PATH%"

REM 如果程序异常退出，显示错误信息
if errorlevel 1 (
    echo.
    echo 程序执行完成，返回码: %errorlevel%
    pause
)

endlocal
