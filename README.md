# AnySound

Converte vídeos (MP4, MKV, AVI, MOV, WEBM, MPEG-TS .ts/.m2ts/.mts...) em áudio: **MP3, WAV, FLAC, OGG, M4A, OPUS**.
Um único `AnySound.exe` — sem instalação; o FFmpeg já vem embutido.

## Equalizar volume das vozes
Marque **Equalizar volume das vozes** para aproximar o volume de vários locutores ou de quem fala longe do microfone. O app aplica, nesta ordem, um normalizador dinâmico, um compressor, a normalização de loudness (-16 LUFS) e um limitador de pico (cerca de -1,5 dB). A saída fica em 48 kHz.

## Como usar
1. Abra o `AnySound.exe`.
2. Clique em **Adicionar vídeos...** (vários de uma vez) ou arraste vídeos e pastas para a janela.
3. Escolha o formato e a qualidade.
4. Clique em **Converter**. Os áudios ficam na pasta do vídeo (ou na pasta escolhida).

## Baixar o .exe
Cada push gera o executável pelo GitHub Actions: aba **Actions → Build AnySound.exe → Artifacts → AnySound**.

## Gerar localmente (Windows)
Com Python 3.9+ instalado, dê dois cliques no `build.bat` (ou, no PowerShell, rode `.\build.bat`). O executável sai em `dist\AnySound.exe`.
