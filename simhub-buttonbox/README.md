# Button Box ETS2: plugin do SimHub

Plugin que adiciona a button box (Arduino Pro Micro/Leonardo) ao SimHub, com uma tela própria no menu esquerdo para configurar:

- **Relé do pisca-alerta** (padrão: pino 15): pino, comportamento (contínuo / sincronizado / original) e teste ligado/desligado
- **Relé da meia-luz** (padrão: pino 10): pino e teste
- **Relé liga com LOW ou HIGH**
- **Botão/chave do Kadett** (padrão: pino 14): pino, número do botão do gamepad, pulso por mudança / ao apertar / segue estado, e duração do pulso
- **Estado ao vivo** (jogo → relé) e as propriedades do jogo usadas (aba Avançado)

Os pinos podem ser trocados **sem regravar o Arduino**: o plugin envia a configuração junto com os dados.
Os pinos 16 (LEDs WS2812B) e 9 (botão do SimHub) ficam bloqueados.

## 1. Compilar e instalar o plugin

1. Instale o **Visual Studio 2022 Community** com a carga de trabalho **"Desenvolvimento para desktop com .NET"**.
2. Abra `ButtonBoxPlugin/ButtonBoxPlugin.csproj`. Se o SimHub não estiver em `C:\Program Files (x86)\SimHub`, ajuste `SimHubDir` no `.csproj`.
3. Compile (**Build**). Com o Visual Studio aberto como administrador, a DLL `User.ButtonBoxETS2.dll` é copiada sozinha para a pasta do SimHub. Senão, copie manualmente de `bin\Debug\net48\`.
4. Abra o SimHub e aceite o aviso de **novo plugin**. Ele aparece no menu esquerdo como **Button Box ETS2**. Se não aparecer: Settings → Plugins → marque *Button Box ETS2*.

## 2. Arduino

1. Substitua o `SHCustomProtocol.h` da sua pasta `DisplayClientV2` pelo arquivo `arduino/SHCustomProtocol.h`.
2. Grave no Arduino como antes, mantendo os mesmos LEDs, o gamepad e o botão do pino 9.

## 3. Ligar os dois

SimHub → **Arduino → My hardware → Custom Protocol**: apague a fórmula antiga e coloque

```
[ButtonBoxPlugin.Mensagem]
```

(o botão **Copiar fórmula** na tela do plugin faz isso.)

## 4. ETS2

Opções → Controles → **Pisca-alerta** → acione a chave do Kadett. O padrão é o **botão 11** do gamepad, que pode ser trocado na tela.

## O que mudou em relação ao código antigo

- **`Joystick.sendState()`**: o firmware do SimHub inicia o joystick com `Joystick.begin(false)`, ou seja, sem envio automático. Sem `sendState()`, o pulso podia nunca chegar ao Windows.
- **Botão do gamepad 0 → 10**: o botão 0 já era usado pelo botão do pino 9 do SimHub.
- **Debounce sem `delay(30)`**: o `delay` travava a leitura dos LEDs e da serial.
- **SimHub fechado**: depois de 3 s sem dados, os relés desligam em vez de ficarem presos ligados.
- O **comportamento do pisca-alerta** agora é escolhido na tela. "Original" mantém a lógica antiga (relé ligado só quando o alerta está ativo **e** as duas setas estão apagadas, ou seja, nos intervalos da piscada). Se você quer o relé ligado o tempo todo com o alerta ativo, use "Contínuo".

## Formato da mensagem (plugin → Arduino)

```
77;alerta;meiaLuz;pinoPisca;pinoMeiaLuz;releAtivoLow;pinoBotao;botaoGamepad(0-33);pulsoMs;modoBotao\n
```
