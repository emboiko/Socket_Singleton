@echo off
REM Publish Socket_Singleton to PyPI
REM Usage: publish.bat

echo Installing build dependencies...
pip install --upgrade build twine

echo Cleaning previous builds...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist *.egg-info rmdir /s /q *.egg-info

echo Building package...
python -m build

echo Checking package...
twine check dist/*

echo.
echo Build complete! Files created in dist/:
dir dist

echo.
echo To upload to PyPI, run:
echo   twine upload dist/*
echo.
echo To upload to TestPyPI first (recommended), run:
echo   twine upload --repository testpypi dist/*

