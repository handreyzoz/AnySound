@echo off
cd /d "%~dp0"
python -m pip install -r requirements.txt || goto :erro
python -m PyInstaller --noconfirm --windowed --name AnySound --icon anysound.ico --add-data "anysound.ico;." --collect-data imageio_ffmpeg --collect-all tkinterdnd2 anysound.py || goto :erro
set ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe
if not exist "%ISCC%" set ISCC=%LocalAppData%\Programs\Inno Setup 6\ISCC.exe
if not exist "%ISCC%" (
  echo.
  echo App pronto em dist\AnySound\AnySound.exe
  echo Para gerar o instalador, instale o Inno Setup 6 ^(jrsoftware.org^) e rode de novo.
  pause
  exit /b 0
)
"%ISCC%" installer.iss || goto :erro
echo.
echo Instalador pronto: dist\AnySound-Setup.exe
pause
exit /b 0
:erro
echo.
echo Falhou. Verifique se o Python esta instalado (python.org, marque "Add Python to PATH").
pause
exit /b 1
