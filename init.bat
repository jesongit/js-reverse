@echo off
chcp 65001 >nul
echo ========================================
echo         js-reverse 项目初始化
echo ========================================
echo.

:: 检查 js-reverse-mcp 目录是否存在
if exist "js-reverse-mcp" (
    echo [信息] js-reverse-mcp 目录已存在，跳过克隆步骤
    echo.
) else (
    echo [步骤 1/3] 克隆 js-reverse-mcp 子模块...
    git clone https://github.com/zhizhuodemao/js-reverse-mcp.git
    if errorlevel 1 (
        echo [错误] 克隆失败，请检查网络连接
        pause
        exit /b 1
    )
    echo [完成] 子模块克隆成功
    echo.
)

:: 进入 js-reverse-mcp 目录
cd /d "%~dp0js-reverse-mcp"

:: 检查 node_modules 是否存在
if exist "node_modules" (
    echo [信息] node_modules 已存在，跳过依赖安装
    echo.
) else (
    echo [步骤 2/3] 安装依赖...
    call npm install
    if errorlevel 1 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
    echo [完成] 依赖安装成功
    echo.
)

:: 构建项目
echo [步骤 3/3] 构建项目...
call npm run build
if errorlevel 1 (
    echo [错误] 项目构建失败
    pause
    exit /b 1
)
echo [完成] 项目构建成功
echo.

:: 返回上级目录
cd /d "%~dp0"

echo ========================================
echo         初始化完成！
echo ========================================
echo.
echo 后续操作：
echo   1. 配置 Claude Code 的 MCP 设置
echo   2. 运行 npm run start 启动 MCP 服务器
echo   3. 或使用 npx js-reverse-mcp 直接运行
echo.
pause
