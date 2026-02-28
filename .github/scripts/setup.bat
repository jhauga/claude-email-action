@echo off
REM =============================================================================
REM setup.bat  -  Windows setup script for Email Agent
REM
REM Creates config.yaml and tasks/mappings.yaml from templates.
REM These files contain sensitive data and are ignored by git.
REM =============================================================================

setlocal enabledelayedexpansion

echo.
echo ============================================
echo   Email Agent Setup (Windows)
echo ============================================
echo.

REM Get the script directory (where this script lives)
set "SCRIPT_DIR=%~dp0"

REM Navigate to project root (two levels up from .github/scripts/)
cd /d "%SCRIPT_DIR%..\.."
set "PROJECT_ROOT=%cd%"

echo Project root: %PROJECT_ROOT%
echo.

REM -----------------------------------------------------------------------------
REM Create config.yaml
REM -----------------------------------------------------------------------------
REM Define template directory
set "TEMPLATE_DIR=%PROJECT_ROOT%\.github\scripts\template"

if exist "%PROJECT_ROOT%\config.yaml" (
    echo [SKIP] config.yaml already exists
) else (
    if exist "%TEMPLATE_DIR%\config.template.yaml" (
        copy "%TEMPLATE_DIR%\config.template.yaml" "%PROJECT_ROOT%\config.yaml" >nul
        echo [DONE] Created config.yaml from template
        echo        ^> Edit config.yaml with your email credentials
    ) else (
        echo [ERROR] Template config.template.yaml not found!
    )
)

REM -----------------------------------------------------------------------------
REM Create tasks/mappings.yaml
REM -----------------------------------------------------------------------------
if not exist "%PROJECT_ROOT%\tasks" (
    mkdir "%PROJECT_ROOT%\tasks"
    echo [DONE] Created tasks/ directory
)

if exist "%PROJECT_ROOT%\tasks\mappings.yaml" (
    echo [SKIP] tasks/mappings.yaml already exists
) else (
    if exist "%TEMPLATE_DIR%\mappings.template.yaml" (
        copy "%TEMPLATE_DIR%\mappings.template.yaml" "%PROJECT_ROOT%\tasks\mappings.yaml" >nul
        echo [DONE] Created tasks/mappings.yaml from template
        echo        ^> Edit tasks/mappings.yaml with your task configurations
    ) else (
        echo [ERROR] Template mappings.template.yaml not found!
    )
)

REM -----------------------------------------------------------------------------
REM Create empty sent_log.json if it doesn't exist
REM -----------------------------------------------------------------------------
if exist "%PROJECT_ROOT%\sent_log.json" (
    echo [SKIP] sent_log.json already exists
) else (
    echo {} > "%PROJECT_ROOT%\sent_log.json"
    echo [DONE] Created empty sent_log.json
)

echo.
echo ============================================
echo   Setup Complete!
echo ============================================
echo.
echo IMPORTANT: Before running the agent:
echo   1. Edit config.yaml with your CPanel email credentials
echo   2. Edit tasks/mappings.yaml with your task mappings
echo.
echo WARNING: These files contain sensitive data!
echo          They are already in .gitignore and will NOT be committed.
echo.
echo To start the agent: python agent.py
echo.

endlocal
pause
