@echo off
REM GameForge Production Phase 2 Build Script - Simple Batch Version

echo ====================================
echo GameForge Production Phase 2 Build
echo ====================================

REM Check if Docker is available
docker version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not available
    exit /b 1
)

echo Docker: Available

REM Set build parameters
set BUILD_DATE=%date:~-4,4%-%date:~-10,2%-%date:~-7,2%T%time:~0,2%:%time:~3,2%:%time:~6,2%Z
set VCS_REF=latest
set BUILD_VERSION=test-build
set VARIANT=%1
if "%VARIANT%"=="" set VARIANT=cpu

echo Build Info:
echo   Variant: %VARIANT%
echo   Date: %BUILD_DATE%
echo   Version: %BUILD_VERSION%

REM Generate image tag
set IMAGE_TAG=gameforge:%BUILD_VERSION%-%VARIANT%

echo Building: %IMAGE_TAG%
echo.

REM Execute Docker build
docker build ^
  -f Dockerfile.production.enhanced ^
  -t %IMAGE_TAG% ^
  --build-arg BUILD_DATE=%BUILD_DATE% ^
  --build-arg VCS_REF=%VCS_REF% ^
  --build-arg BUILD_VERSION=%BUILD_VERSION% ^
  --build-arg VARIANT=%VARIANT% ^
  --build-arg PYTHON_VERSION=3.10 ^
  .

if errorlevel 1 (
    echo ERROR: Build failed
    exit /b 1
) else (
    echo SUCCESS: Build completed
    docker images %IMAGE_TAG%
)

echo.
echo Build completed successfully!
