@ECHO OFF
call .\venv\Scripts\activate.bat
echo Installing requirements.txt
python -m pip install pip -r requirements.txt -U --no-cache-dir --force-reinstall
echo Installed requirements.txt
PAUSE