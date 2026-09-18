@echo off
chcp 65001 >nul
echo ============================================
echo  TradingAgents - XAUUSD (Gold / USD)
echo ============================================
echo.
set AUTO_RUN=1
set AUTO_RUN_TICKER=XAUUSD
python -m cli.main
pause
