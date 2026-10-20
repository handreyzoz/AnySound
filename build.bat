@echo off
cd /d "%~dp0"
python -m pip install -r requirements.txt || goto :erro
python -m PyInstaller --onefile --windowed --name AnySound --collect-data imageio_ffmpeg --collect-all tkinterdnd2 anysound.py || goto :erro
echo.
echo Pronto: dist\AnySound.exe
pause
exit /b 0
:erro
echo.
echo Falhou. Verifique se o Python esta instalado (python.org, marque "Add Python to PATH").
pause
exit /b 1
