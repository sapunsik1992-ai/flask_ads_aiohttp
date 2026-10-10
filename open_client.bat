@echo off
cd /d "%~dp0"
if exist server_port.txt (
    for /f "delims=" %%i in (server_port.txt) do start http://127.0.0.1:%%i/
) else (
    start http://127.0.0.1:5000/
)
