namespace ButtonBoxETS2
{
    /// <summary>Configurações salvas pelo SimHub (PluginsData\Common\ButtonBoxPlugin.Configuracoes.json).</summary>
    public class ButtonBoxSettings
    {
        // Relé do pisca-alerta
        public bool AlertaAtivo { get; set; } = true;
        public int PinoPisca { get; set; } = 15;
        /// <summary>0 = contínuo, 1 = sincronizado com o pisca, 2 = original (ligado nos intervalos).</summary>
        public int ModoAlerta { get; set; } = 2;

        // Relé da meia-luz
        public bool MeiaLuzAtiva { get; set; } = true;
        public int PinoMeiaLuz { get; set; } = 10;

        /// <summary>Módulos de relé comuns ligam com LOW.</summary>
        public bool ReleAtivoEmLow { get; set; } = true;

        // Botão/chave do Kadett
        public int PinoBotao { get; set; } = 14;
        /// <summary>Número do botão como o Windows mostra (1 a 34). O botão 1 é do pino 9 do SimHub.</summary>
        public int BotaoGamepad { get; set; } = 11;
        public int PulsoMs { get; set; } = 80;
        /// <summary>0 = pulso a cada mudança (chave liga/desliga), 1 = pulso ao apertar, 2 = segue o estado.</summary>
        public int ModoBotao { get; set; } = 0;

        // Propriedades do jogo (podem ser trocadas na tela de configuração)
        public string PropAlerta { get; set; } = "DataCorePlugin.GameRawData.TruckValues.CurrentValues.LightsValues.HazardWarningLights";
        public string PropSetaEsquerda { get; set; } = "DataCorePlugin.GameRawData.TruckValues.CurrentValues.LightsValues.BlinkerLeftOn";
        public string PropSetaDireita { get; set; } = "DataCorePlugin.GameRawData.TruckValues.CurrentValues.LightsValues.BlinkerRightOn";
        public string PropMeiaLuz { get; set; } = "DataCorePlugin.GameRawData.TruckValues.CurrentValues.LightsValues.Parking";

        public bool SomenteETS2ATS { get; set; } = true;
    }
}
