@echo off
REM 意识系统快速演示脚本
REM 用于Windows环境

echo ========================================
echo   AutoAI 意识系统快速演示
echo ========================================
echo.

REM 设置UTF-8编码
chcp 65001 >nul

REM 运行测试
python autoai/agents/test_consciousness_system.py

echo.
echo ========================================
echo   演示完成！
echo ========================================
pause
