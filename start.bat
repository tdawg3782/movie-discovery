@echo off
echo Starting Movie Discovery App...
echo.

:: Start backend in a new terminal
echo Starting Backend (FastAPI) on http://localhost:8000
start "Movie Discovery - Backend" cmd /k "cd /d %~dp0backend && uvicorn src.app.main:app --reload"

:: Wait a moment for backend to initialize
timeout /t 2 /nobreak >nul

:: Start frontend in a new terminal
echo Starting Frontend (Vue) on http://localhost:3000
start "Movie Discovery - Frontend" cmd /k "cd /d %~dp0frontend && npm.cmd run dev"

echo.
echo Servers starting in separate windows...
echo.
echo   Backend API:  http://localhost:8000
echo   Frontend UI:  http://localhost:3000
echo   API Docs:     http://localhost:8000/docs
echo.
echo Run stop.bat to shut down both servers.
