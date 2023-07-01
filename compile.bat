@ECHO OFF
set name = "Trove File Extractor"
set version = "0.1.000"
set author = "Sly"
call .\venv\Scripts\activate.bat
echo Compiling Executable
flet pack --icon="assets/favicon.ico" --add-data="assets;assets" --product-name="%name%" --file-description="%name%" --product-version="%version%" --file-version="%version%" --company-name="%author%" --copyright="%author%" main.py
PAUSE