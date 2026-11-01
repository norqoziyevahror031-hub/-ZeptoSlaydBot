@echo off
chcp 65001 >nul
title ZeptoSlaydBot - Windows Avtomatik Ishga Tushirishni O'chirish
cd /d "%~dp0"

echo ====================================================================
echo    ZEPTO SLAYD BOT - AVTO-YUKLANISHNI O'CHIRISH
echo ====================================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "
$startupFolder = [System.IO.Path]::Combine($env:APPDATA, 'Microsoft\Windows\Start Menu\Programs\Startup')
$shortcutPath = Join-Path $startupFolder 'ZeptoSlaydBot.lnk'
if (Test-Path $shortcutPath) {
    Remove-Item $shortcutPath -Force
    Write-Host 'Windows Startup yorlig''i o''chirildi!' -ForegroundColor Green
} else {
    Write-Host 'Avto-yuklanish yorlig''i topilmadi.' -ForegroundColor Yellow
}
"

echo.
pause
