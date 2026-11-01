@echo off
chcp 65001 >nul
title ZeptoSlaydBot - Holatni tekshirish
cd /d "%~dp0"

echo ====================================================
echo        ZEPTO SLAYD BOT - HOLATNI TEKSHIRISH
echo ====================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "
$procs = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -like '*main.py*' -and $_.ProcessId -ne $PID
}
if ($procs) {
    Write-Host 'HOLAT: BOT FONDA ISHLAYAPTI! [24/7 ONLINE]' -ForegroundColor Green
    foreach ($p in $procs) {
        $procInfo = Get-Process -Id $p.ProcessId -ErrorAction SilentlyContinue
        $memMB = [math]::Round($procInfo.WorkingSet64 / 1MB, 2)
        Write-Host ('  - PID: ' + $p.ProcessId + ' | Xotira: ' + $memMB + ' MB | Boshlangan vaqt: ' + $procInfo.StartTime) -ForegroundColor Cyan
    }
} else {
    Write-Host 'HOLAT: BOT HOZIRDA TO''XTATILGAN (ISHLAMAYAPTI).' -ForegroundColor Red
    Write-Host 'Botni ishga tushirish uchun "run_bot.bat" yoki "start_background.vbs" ni bosing.' -ForegroundColor Yellow
}
"

echo.
echo ----------------------------------------------------
echo So'nggi loglar (bot.log):
echo ----------------------------------------------------
powershell -NoProfile -ExecutionPolicy Bypass -Command "
if (Test-Path 'bot.log') {
    Get-Content 'bot.log' -Tail 10
} else {
    Write-Host 'Hozircha bot.log fayli mavjud emas.' -ForegroundColor Gray
}
"

echo ----------------------------------------------------
echo.
pause
