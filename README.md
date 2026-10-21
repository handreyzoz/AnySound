# AnySound

Arraste um vídeo ou áudio para a janela e pronto: o AnySound converte para áudio e/ou equaliza o volume das vozes. Sem botão de "converter".

## Instalar
Baixe `AnySound-Setup.exe` (aba **Actions → Build AnySound → Artifacts → AnySound-Setup**) e execute.
O instalador deixa escolher a pasta (padrão `C:\Program Files\AnySound`), cria atalho no Menu Iniciar e, se quiser, na área de trabalho. O FFmpeg já vem junto.

## Como usar
Antes de arrastar, escolha na barra de cima:

- **Formato**
  - **Manter formato**: o arquivo continua do mesmo tipo (um vídeo continua vídeo). O vídeo é copiado sem perda e só o áudio é tratado. Sai como `nome (normalizado).mp4`.
  - **MP3, WAV, FLAC, OGG, M4A, OPUS**: extrai o áudio nesse formato.
- **Equalizar volume**: aproxima o volume de vários locutores ou de quem fala longe do microfone, de forma suave (filtro de graves, normalizador dinâmico, compressor, loudness -16 LUFS e limitador). Liga ou desliga tudo junto.
- **•••**: configurações (pasta de saída, qualidade, abrir a pasta ao terminar).

Depois é só arrastar arquivos ou pastas. Vários arquivos entram numa fila. Aceita MP4, MKV, AVI, MOV, WEBM, MPEG-TS (.ts/.m2ts/.mts) e outros, além de áudios (MP3, WAV, FLAC...).

## Gerar localmente (Windows)
Com Python 3.9+ instalado, dê dois cliques em `build.bat` (no PowerShell: `.\build.bat`).
Sai o app em `dist\AnySound\`; se o [Inno Setup 6](https://jrsoftware.org/isinfo.php) estiver instalado, também `dist\AnySound-Setup.exe`.
