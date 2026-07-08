@echo off
setlocal
rem Launch TestPython.py with Python 3.10 (the one we built opencv_wrapper.cp310 for).
rem %~dp0 = directory of this .bat (with trailing backslash), so it works no
rem matter where Run.bat is invoked from.

py -3.10 "%~dp0TestPython.py"
set RC=%ERRORLEVEL%

echo.
echo --- Done. Exit code: %RC% ---
pause
endlocal
