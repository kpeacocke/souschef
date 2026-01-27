@echo off
REM CodeQL Database Build and Analysis Script for Windows
REM Works on Windows Command Prompt and PowerShell
REM Usage: codeql-analyze.bat [build|analyze|clean|rebuild]

setlocal enabledelayedexpansion

REM Set paths
set "PROJECT_ROOT=."
set "CODEQL_DIR=.codeql"
set "DB_DIR=!CODEQL_DIR!\databases\python-db"
set "CONFIG_DIR=!CODEQL_DIR!\config"
set "REPORTS_DIR=!CODEQL_DIR!\reports"
set "CODEQLIGNORE=!CONFIG_DIR!\.codeqlignore"

REM Color codes won't work in all Windows terminals, so we'll skip them
REM Just use clear text with prefixes

if "%1"=="" (
    call :analyze
    goto :end
) else if "%1"=="build" (
    call :build
    goto :end
) else if "%1"=="analyze" (
    call :analyze
    goto :end
) else if "%1"=="rebuild" (
    call :rebuild
    goto :end
) else if "%1"=="clean" (
    call :clean
    goto :end
) else if "%1"=="help" (
    call :help
    goto :end
) else (
    echo [ERROR] Unknown command: %1
    call :help
    exit /b 1
)

:end
exit /b 0

REM ===== Functions =====

:check_codeql
echo [CodeQL] Checking CodeQL CLI installation...
where codeql >nul 2>&1
if errorlevel 1 (
    echo [ERROR] CodeQL CLI is not installed or not in PATH
    echo Install from: https://github.com/github/codeql-cli-binaries/releases
    exit /b 1
)
for /f "tokens=*" %%i in ('codeql version') do set "CODEQL_VERSION=%%i"
echo [OK] CodeQL CLI found: !CODEQL_VERSION!
exit /b 0

:build
call :check_codeql
if errorlevel 1 exit /b 1

echo [CodeQL] Building CodeQL database for Python...

if exist "!DB_DIR!" (
    echo [WARNING] Database already exists at !DB_DIR!
    set /p RESPONSE="Delete and rebuild? (y/N): "
    if /i "!RESPONSE!"=="y" (
        rmdir /s /q "!DB_DIR!"
        echo [CodeQL] Removed existing database
    ) else (
        echo [WARNING] Skipping database rebuild
        exit /b 0
    )
)

if not exist "!DB_DIR!" mkdir "!DB_DIR!"

echo [CodeQL] Creating database (this may take several minutes)...
codeql database create "!DB_DIR!" ^
    --language=python ^
    --source-root="!PROJECT_ROOT!" ^
    --codescanning-config="!CONFIG_DIR!\config.yml" ^
    --source-map-filters="!CODEQLIGNORE!" ^
    --skip-classification

if errorlevel 1 (
    echo [ERROR] Failed to create CodeQL database
    rmdir /s /q "!DB_DIR!" 2>nul
    exit /b 1
)

echo [OK] CodeQL database created successfully
exit /b 0

:analyze
call :check_codeql
if errorlevel 1 exit /b 1

echo [CodeQL] Running CodeQL analysis...

if not exist "!DB_DIR!" (
    echo [ERROR] Database not found. Run 'build' first.
    exit /b 1
)

if not exist "!REPORTS_DIR!" mkdir "!REPORTS_DIR!"

REM Archive previous latest.sarif
if exist "!REPORTS_DIR!\latest.sarif" (
    for /f "tokens=2-4 delims=/- " %%a in ('date /t') do (
        set "DATEPART=%%c%%a%%b"
    )
    for /f "tokens=1-2 delims=/:" %%a in ('time /t') do (
        set "TIMEPART=%%a%%b"
    )
    set "TIMESTAMP=!DATEPART!-!TIMEPART!"
    move "!REPORTS_DIR!\latest.sarif" "!REPORTS_DIR!\archive\!TIMESTAMP!.sarif"
    echo [CodeQL] Archived previous report to archive\!TIMESTAMP!.sarif
)

echo [CodeQL] Starting analysis (this may take a few minutes)...
codeql database analyze "!DB_DIR!" ^
    --format=sarif-latest ^
    --output="!REPORTS_DIR!\latest.sarif" ^
    codeql/python-queries:codeql-suites/python-security-and-quality.qls

if errorlevel 1 (
    echo [ERROR] CodeQL analysis failed
    exit /b 1
)

echo [OK] Analysis complete - results in !REPORTS_DIR!\latest.sarif
exit /b 0

:rebuild
call :build
if errorlevel 1 exit /b 1
call :analyze
exit /b 0

:clean
echo [CodeQL] Cleaning CodeQL databases...

if exist "!DB_DIR!" (
    rmdir /s /q "!DB_DIR!"
    echo [OK] Removed database at !DB_DIR!
)

if not exist "!DB_DIR!" mkdir "!DB_DIR!"
type nul > "!DB_DIR!\.gitkeep"
echo [OK] Database directory reset
exit /b 0

:help
echo.
echo CodeQL Analysis Tool for Windows
echo.
echo Usage: %0 [COMMAND]
echo.
echo Commands:
echo   build       Build the CodeQL database (from scratch^)
echo   analyze     Run CodeQL analysis on existing database
echo   rebuild     Clean and rebuild everything (build + analyze^)
echo   clean       Remove CodeQL databases (keeps configuration and reports^)
echo   help        Show this help message
echo.
echo Examples:
echo   REM First time setup
echo   %0 build
echo   %0 analyze
echo.
echo   REM After code changes
echo   %0 analyze
echo.
echo   REM Start fresh
echo   %0 rebuild
echo.
echo The directory structure:
echo   .codeql\
echo     ├── config\        Configuration files (committed^)
echo     ├── databases\     CodeQL databases (local only, ignored^)
echo     ├── reports\       SARIF analysis results (committed^)
echo     └── queries\       Custom queries (committed^)
echo.
exit /b 0
