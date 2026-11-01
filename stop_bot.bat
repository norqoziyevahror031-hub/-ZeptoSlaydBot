@echo off
chcp 65001 >nul
title ZeptoSlaydBot - To'xtatish
cd /d "%~dp0"

echo ====================================================
echo        ZEPTO SLAYD BOTNI TO'XTATISH
echo ====================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "
$procs = Get-CimInstance Win32_Process | Where-Object {
    ($_.CommandLine -like '*main.py*' -or $_.CommandLine -like '*run_bot.bat*') -and $_.ProcessId -ne $PID
}
if ($procs) {
    foreach ($p in $procs) {
        Write-Host ('To''xtatilmoqda: PID ' + $p.ProcessId + ' (' + $p.Name + ')') -ForegroundColor Yellow
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Write-Host 'Bot muvaffaqiyatli to''xtatildi!' -ForegroundColor Green
} else {
    Write-Host 'Ishlayotgan bot jarayoni topilmadi.' -ForegroundColor Cyan
}
"

echo.
pause
