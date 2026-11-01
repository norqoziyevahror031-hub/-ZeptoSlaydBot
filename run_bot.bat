@echo off
chcp 65001 >nul
title ZeptoSlaydBot - 24/7 Runner
cd /d "%~dp0"

echo ====================================================
echo        ZEPTO SLAYD BOT - 24/7 ISHGA TUSHIRISH
echo ====================================================
echo.
echo Bot ishga tushmoqda...
echo Barcha loglar "bot.log" fayliga yozib boriladi.
echo To'xtatish uchun: Ctrl + C bosing.
echo.

:loop
echo [%date% %time%] Bot ishga tushirilmoqda...
where python >nul 2>nul
if %errorlevel% equ 0 (
    python main.py
) else (
    py main.py
)
if %errorlevel% neq 0 (
    echo.
    echo [%date% %time%] DIQQAT: Bot to'xtadi yoki xatolik yuz berdi (kod: %errorlevel%).
    echo 5 soniyadan so'ng avtomatik qayta ishga tushiriladi...
) else (
    echo.
    echo [%date% %time%] Bot to'xtatildi. 5 soniyadan so'ng qayta ishga tushiriladi...
)

timeout /t 5 /nobreak >nul
echo.
echo [%date% %time%] Qayta ishga tushirish amalga oshirilmoqda...
goto loop
