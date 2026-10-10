@echo off
cd /d "%~dp0"
del /q server_port.txt 2>nul
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    start "Aiohttp Ads Server" cmd /k py -3 server.py
) else (
    start "Aiohttp Ads Server" cmd /k python server.py
)
:wait_port
if exist server_port.txt (
    for /f "delims=" %%i in (server_port.txt) do start http://127.0.0.1:%%i/
    exit /b 0
)
ping -n 1 127.0.0.1 >nul
goto wait_port
