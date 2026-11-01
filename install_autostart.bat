@echo off
chcp 65001 >nul
title ZeptoSlaydBot - Windows Avtomatik Ishga Tushirishni O'rnatish
cd /d "%~dp0"

echo ====================================================================
echo    ZEPTO SLAYD BOT - WINDOWS AVTO-YUKLANISHGA SOZLASH (24/7)
echo ====================================================================
echo.
echo Kompyuter yoqilishi bilan bot avtomatik fonda ishga tushadigan
echo qilib sozlanmoqda...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $scriptDir) { $scriptDir = (Get-Location).Path }
$vbsPath = Join-Path $scriptDir 'start_background.vbs'
$startupFolder = [System.IO.Path]::Combine($env:APPDATA, 'Microsoft\Windows\Start Menu\Programs\Startup')
$shortcutPath = Join-Path $startupFolder 'ZeptoSlaydBot.lnk'

$wshShell = New-Object -ComObject WScript.Shell
$shortcut = $wshShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = 'wscript.exe'
$shortcut.Arguments = '\"' + $vbsPath + '\"'
$shortcut.WorkingDirectory = $scriptDir
$shortcut.Description = 'Zepto Slayd Telegram Bot 24/7 avtomatik yuklanish'
$shortcut.Save()

Write-Host 'Muvaffaqiyatli o''rnatildi!' -ForegroundColor Green
Write-Host ('Yorliq manzili: ' + $shortcutPath) -ForegroundColor Cyan
Write-Host 'Endi kompyuter har safar yoqilganda bot avtomatik fonda ishlaydi!' -ForegroundColor Green
"

echo.
echo O'rnatish yakunlandi.
echo.
pause
