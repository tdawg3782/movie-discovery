@echo off
echo Stopping Movie Discovery App...
echo.

:: Kill uvicorn (Python) processes
echo Stopping Backend...
taskkill /f /im uvicorn.exe 2>nul
taskkill /f /fi "WINDOWTITLE eq Movie Discovery - Backend*" 2>nul

:: Kill node processes (Vite dev server)
echo Stopping Frontend...
taskkill /f /fi "WINDOWTITLE eq Movie Discovery - Frontend*" 2>nul

:: Kill any remaining node processes on port 5173
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173" ^| findstr "LISTENING"') do (
    taskkill /f /pid %%a 2>nul
)

:: Kill any remaining python processes on port 8000
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /f /pid %%a 2>nul
)

echo.
echo Servers stopped.
