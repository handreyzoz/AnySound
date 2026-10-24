#ifndef __SHCUSTOMPROTOCOL_H__
#define __SHCUSTOMPROTOCOL_H__

#include "Arduino.h"

//=================================================
// BUTTON BOX ETS2
//
// Tudo é configurado pelo plugin "Button Box ETS2" no SimHub.
// Fórmula do Custom Protocol:  [ButtonBoxPlugin.Mensagem]
//
// Mensagem recebida (uma linha):
// 77;alerta;meiaLuz;pinoPisca;pinoMeiaLuz;releAtivoLow;pinoBotao;botaoGamepad;pulsoMs;modoBotao
//
// Pinos usados pelo firmware do SimHub (não usar aqui):
//   16 = LEDs WS2812B    9 = botão do SimHub (botão 1 do gamepad)
//=================================================

#define BB_MAGIC 77
#define BB_TIMEOUT_MS 3000   // sem mensagens do SimHub -> desliga os relés
#define BB_DEBOUNCE_MS 30

// Modos do botão
#define BB_PULSO_MUDANCA 0   // chave liga/desliga: pulso a cada mudança
#define BB_PULSO_APERTAR 1   // botão de pressão: pulso só ao apertar
#define BB_SEGUE_ESTADO  2   // botão do gamepad fica apertado junto

class SHCustomProtocol {

private:

  // Valores iniciais (usados até chegar a primeira mensagem do plugin)
  byte pinoRelePisca = 15;
  byte pinoReleMeiaLuz = 10;
  byte pinoBotao = 14;
  bool releAtivoLow = true;
  byte botaoGamepad = 10;          // botão 11 no Windows
  unsigned long tempoPulso = 80;
  byte modoBotao = BB_PULSO_MUDANCA;

  bool alerta = false;
  bool meiaLuz = false;
  unsigned long ultimaMensagem = 0;

  bool leituraAnterior = HIGH;
  bool estadoBotao = HIGH;
  unsigned long inicioDebounce = 0;
  bool pulsoAtivo = false;
  unsigned long inicioPulso = 0;

  static bool pinoValido(int p) {
    return p >= 0 && p <= 21 && p != 16 && p != 9;
  }

  void escreverRele(byte pino, bool ligado) {
    // ligado + ativo em LOW -> LOW
    digitalWrite(pino, (ligado != releAtivoLow) ? HIGH : LOW);
  }

  void atualizarReles() {
    escreverRele(pinoRelePisca, alerta);
    escreverRele(pinoReleMeiaLuz, meiaLuz);
  }

  void configurarPinoRele(byte &atual, byte novo) {
    if (novo == atual) return;
    pinMode(atual, INPUT);   // solta o pino antigo
    atual = novo;
    pinMode(atual, OUTPUT);
    escreverRele(atual, false);
  }

  void botaoGamepadPressionado(bool pressionado) {
#ifdef INCLUDE_GAMEPAD
    Joystick.setButton(botaoGamepad, pressionado);
    // O SimHub usa Joystick.begin(false): sem sendState() nada é enviado
    Joystick.sendState();
#endif
  }

  void iniciarPulso() {
    botaoGamepadPressionado(true);
    pulsoAtivo = true;
    inicioPulso = millis();
  }

public:

  void setup() {
    pinMode(pinoRelePisca, OUTPUT);
    pinMode(pinoReleMeiaLuz, OUTPUT);
    atualizarReles();

    pinMode(pinoBotao, INPUT_PULLUP);
    leituraAnterior = estadoBotao = digitalRead(pinoBotao);
  }

  void read() {
    int magic = FlowSerialReadStringUntil(';').toInt();
    if (magic != BB_MAGIC) {
      // Mensagem de outra fórmula: descarta
      FlowSerialReadStringUntil('\n');
      return;
    }

    int v[9];
    for (byte i = 0; i < 8; i++) {
      v[i] = FlowSerialReadStringUntil(';').toInt();
    }
    v[8] = FlowSerialReadStringUntil('\n').toInt();

    alerta = v[0] == 1;
    meiaLuz = v[1] == 1;
    ultimaMensagem = millis();

    int novoPisca = v[2], novoMeiaLuz = v[3], novoBotao = v[5];
    bool pinosOk = pinoValido(novoPisca) && pinoValido(novoMeiaLuz) && pinoValido(novoBotao)
                   && novoPisca != novoMeiaLuz && novoPisca != novoBotao && novoMeiaLuz != novoBotao;

    if (pinosOk) {
      releAtivoLow = v[4] == 1;
      configurarPinoRele(pinoRelePisca, novoPisca);
      configurarPinoRele(pinoReleMeiaLuz, novoMeiaLuz);

      if (novoBotao != pinoBotao) {
        pinMode(pinoBotao, INPUT);
        pinoBotao = novoBotao;
        pinMode(pinoBotao, INPUT_PULLUP);
        leituraAnterior = estadoBotao = digitalRead(pinoBotao);
      }
    }

    if (v[6] >= 1 && v[6] <= 33 && v[6] != botaoGamepad) {
      botaoGamepadPressionado(false);   // solta o botão antigo
      botaoGamepad = v[6];
    }
    if (v[7] >= 20 && v[7] <= 1000) tempoPulso = v[7];
    if (v[8] >= BB_PULSO_MUDANCA && v[8] <= BB_SEGUE_ESTADO) modoBotao = v[8];

    atualizarReles();
  }

  void loop() {
    unsigned long agora = millis();

    // SimHub fechado ou desconectado: desliga os relés
    if ((alerta || meiaLuz) && agora - ultimaMensagem > BB_TIMEOUT_MS) {
      alerta = meiaLuz = false;
      atualizarReles();
    }

    // Debounce sem delay()
    bool leitura = digitalRead(pinoBotao);
    if (leitura != leituraAnterior) {
      leituraAnterior = leitura;
      inicioDebounce = agora;
    }

    if (leitura != estadoBotao && agora - inicioDebounce >= BB_DEBOUNCE_MS) {
      estadoBotao = leitura;
      bool apertado = estadoBotao == LOW;   // botão ligado ao GND

      if (modoBotao == BB_SEGUE_ESTADO) {
        botaoGamepadPressionado(apertado);
      } else if (modoBotao == BB_PULSO_MUDANCA || apertado) {
        iniciarPulso();
      }
    }

    if (pulsoAtivo && agora - inicioPulso >= tempoPulso) {
      botaoGamepadPressionado(false);
      pulsoAtivo = false;
    }
  }

  void idle() {
  }
};

#endif
