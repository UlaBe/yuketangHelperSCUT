# 智能启动器 - 由小辉nuitkaGUI自动生成
# 生成时间: 2025-08-30 23:30:41
# 原始程序: videoHelper.exe

# 设置错误处理
$ErrorActionPreference = "Stop"

try {
    # 获取脚本所在目录
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
    
    # 设置程序路径（相对于脚本位置）
    $ProgramPath = Join-Path $ScriptDir "../videoHelper.exe"
    
    # 检查程序是否存在
    if (-not (Test-Path $ProgramPath)) {
        Write-Error "找不到程序文件: $ProgramPath"
        Read-Host "按Enter键退出"
        exit 1
    }
    
    # 切换到程序所在目录
    $ProgramDir = Split-Path -Parent $ProgramPath
    Set-Location $ProgramDir
    
    # 启动程序
    Write-Host "正在启动: videoHelper.exe"
    & $ProgramPath
    
    # 检查退出代码
    if ($LASTEXITCODE -ne 0) {
        Write-Host "程序执行完成，返回码: $LASTEXITCODE" -ForegroundColor Yellow
        Read-Host "按Enter键退出"
    }
    
} catch {
    Write-Error "启动程序时发生错误: $($_.Exception.Message)"
    Read-Host "按Enter键退出"
    exit 1
}
