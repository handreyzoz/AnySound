@echo off
pip install -r requirements.txt
pyinstaller --onefile --windowed --name AnySound --collect-data imageio_ffmpeg anysound.py
echo.
echo Pronto: dist\AnySound.exe
