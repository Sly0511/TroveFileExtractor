@ECHO OFF
set name = "Trove File Extractor"
set version = "0.1.000"
set author = "Sly"
call .\venv\Scripts\activate.bat
echo Compiling Executable
pyinstaller --onefile --add-data="assets;assets" main.py
PAUSE