@echo off
echo Starting setup...


python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed! Please install Python 3.8 or higher.
    pause
    exit /b 1
)


echo Creating requirements.txt...
pip install pipreqs
pipreqs . --force
if %errorlevel% neq 0 (
    echo Failed to create requirements.txt!
    pause
    exit /b 1
)


echo Creating virtual environment...
python -m venv venv
if %errorlevel% neq 0 (
    echo Failed to create virtual environment!
    pause
    exit /b 1
)


echo Activating virtual environment...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo Failed to activate virtual environment!
    pause
    exit /b 1
)


echo Installing requirements...
python -m pip install --upgrade pip
if %errorlevel% neq 0 (
    echo Failed to upgrade pip!
    pause
    exit /b 1
)

echo Installing packages from requirements.txt...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Failed to install requirements!
    echo Please check the error message above.
    pause
    exit /b 1
)


deactivate


echo Creating updated start.vbs...
echo Set WShell = CreateObject("WScript.Shell") > start.vbs
echo strPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) >> start.vbs
echo WShell.CurrentDirectory = strPath >> start.vbs
echo WShell.Run "cmd /c ""venv\Scripts\activate.bat && pythonw main.py""", 0, False >> start.vbs

echo.
echo Setup completed successfully!
echo You can now run the program using start.vbs
echo.
echo Press any key to exit...
pause >nul 