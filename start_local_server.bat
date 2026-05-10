@echo off
setlocal

cd /d "%~dp0"
set "PORT=8000"
set "HOST=127.0.0.1"

echo Starting local server for NHI Drug Calculator...
echo.
echo URL: http://%HOST%:%PORT%/index.html
echo.
echo Keep this window open while testing.
echo Press Ctrl+C to stop the server.
echo.

python -m http.server %PORT% --bind %HOST%

echo.
echo Server stopped.
pause
