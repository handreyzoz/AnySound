using GameReaderCommon;
using SimHub.Plugins;
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace ButtonBoxETS2
{
    [PluginDescription("Button box (Arduino) do Euro Truck Simulator 2: relés de pisca-alerta e meia-luz e botão do Kadett")]
    [PluginAuthor("handrey")]
    [PluginName("Button Box ETS2")]
    public class ButtonBoxPlugin : IPlugin, IDataPlugin, IWPFSettingsV2
    {
        /// <summary>Primeiro campo da mensagem; o Arduino ignora linhas sem ele.</summary>
        public const int Magic = 77;
        public const int SemPino = 255;

        /// <summary>Pinos já usados pelo firmware do SimHub: 16 = WS2812B, 9 = botão do SimHub.</summary>
        public static readonly int[] PinosReservados = { 9, 16 };
        /// <summary>Pinos digitais livres do Pro Micro / Leonardo.</summary>
        public static readonly int[] PinosLivres = { 0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 14, 15, 18, 19, 20, 21 };

        public const string NomeConfiguracoes = "Configuracoes";

        public ButtonBoxSettings Settings { get; private set; }
        public PluginManager PluginManager { get; set; }

        public ImageSource PictureIcon => Icone.Criar();
        public string LeftMenuTitle => "Button Box ETS2";

        // Modo de teste (não é salvo): 0 = automático, 1 = forçar ligado, 2 = forçar desligado
        public int TesteAlerta { get; set; }
        public int TesteMeiaLuz { get; set; }

        // Estado ao vivo, lido pela tela de configuração
        public bool JogoAtivo { get; private set; }
        public bool AlertaNoJogo { get; private set; }
        public bool MeiaLuzNoJogo { get; private set; }
        public bool AlertaSaida { get; private set; }
        public bool MeiaLuzSaida { get; private set; }
        public string ErroConfiguracao { get; private set; }

        private string configuracaoValida;
        private volatile string mensagem = "";
        public string Mensagem => mensagem;

        public void Init(PluginManager pluginManager)
        {
            Settings = this.ReadCommonSettings(NomeConfiguracoes, () => new ButtonBoxSettings());

            // Usada na fórmula do Custom Protocol do Arduino: [ButtonBoxPlugin.Mensagem]
            this.AttachDelegate("Mensagem", () => mensagem);
            this.AttachDelegate("AlertaLigado", () => AlertaSaida);
            this.AttachDelegate("MeiaLuzLigada", () => MeiaLuzSaida);

            AtualizarConfiguracao();
            mensagem = MontarMensagem(false, false);
        }

        public void DataUpdate(PluginManager pluginManager, ref GameData data)
        {
            var s = Settings;
            bool jogo = data.GameRunning
                && (!s.SomenteETS2ATS || data.GameName == "ETS2" || data.GameName == "ATS");

            bool alertaJogo = jogo && LerBool(pluginManager, s.PropAlerta);
            bool meiaLuzJogo = jogo && LerBool(pluginManager, s.PropMeiaLuz);

            bool alerta = alertaJogo;
            if (s.ModoAlerta != 0)
            {
                bool esquerda = LerBool(pluginManager, s.PropSetaEsquerda);
                bool direita = LerBool(pluginManager, s.PropSetaDireita);
                alerta = s.ModoAlerta == 1
                    ? alertaJogo && esquerda
                    : alertaJogo && !esquerda && !direita;
            }

            JogoAtivo = jogo;
            AlertaNoJogo = alertaJogo;
            MeiaLuzNoJogo = meiaLuzJogo;
            AlertaSaida = Aplicar(s.AlertaAtivo, TesteAlerta, alerta);
            MeiaLuzSaida = Aplicar(s.MeiaLuzAtiva, TesteMeiaLuz, meiaLuzJogo);

            mensagem = MontarMensagem(AlertaSaida, MeiaLuzSaida);
        }

        public void End(PluginManager pluginManager)
        {
            Salvar();
        }

        public Control GetWPFSettingsControl(PluginManager pluginManager)
        {
            return new SettingsControl(this);
        }

        public void Salvar()
        {
            this.SaveCommonSettings(NomeConfiguracoes, Settings);
        }

        /// <summary>Valida os pinos; só uma configuração válida é enviada ao Arduino.</summary>
        public void AtualizarConfiguracao()
        {
            ErroConfiguracao = Validar(Settings);
            if (ErroConfiguracao != null && configuracaoValida != null)
                return;

            var s = ErroConfiguracao == null ? Settings : new ButtonBoxSettings();
            configuracaoValida = string.Join(";",
                s.PinoPisca,
                s.PinoMeiaLuz,
                s.ReleAtivoEmLow ? 1 : 0,
                s.PinoBotao,
                s.BotaoGamepad - 1,
                s.PulsoMs,
                s.ModoBotao);
            mensagem = MontarMensagem(AlertaSaida, MeiaLuzSaida);
        }

        public static string Validar(ButtonBoxSettings s)
        {
            var pinos = new Dictionary<string, int>
            {
                { "relé do pisca-alerta", s.PinoPisca },
                { "relé da meia-luz", s.PinoMeiaLuz },
                { "botão do Kadett", s.PinoBotao },
            };

            foreach (var p in pinos)
            {
                if (PinosReservados.Contains(p.Value))
                    return $"O pino {p.Value} ({p.Key}) já é usado pelo firmware do SimHub.";
                if (!PinosLivres.Contains(p.Value))
                    return $"O pino {p.Value} ({p.Key}) não existe no Pro Micro/Leonardo.";
            }

            var repetido = pinos.GroupBy(p => p.Value).FirstOrDefault(g => g.Count() > 1);
            if (repetido != null)
                return $"O pino {repetido.Key} está em uso por: {string.Join(" e ", repetido.Select(p => p.Key))}.";

            if (s.BotaoGamepad < 2 || s.BotaoGamepad > 34)
                return "O botão do gamepad deve ser de 2 a 34 (o botão 1 é do pino 9).";
            if (s.PulsoMs < 20 || s.PulsoMs > 1000)
                return "O pulso deve ter entre 20 e 1000 ms.";

            return null;
        }

        private string MontarMensagem(bool alerta, bool meiaLuz)
        {
            // 77;alerta;meiaLuz;pinoPisca;pinoMeiaLuz;releAtivoLow;pinoBotao;botaoGamepad;pulsoMs;modoBotao\n
            return $"{Magic};{(alerta ? 1 : 0)};{(meiaLuz ? 1 : 0)};{configuracaoValida}\n";
        }

        private static bool Aplicar(bool ativo, int teste, bool valor)
        {
            if (teste == 1) return true;
            if (teste == 2) return false;
            return ativo && valor;
        }

        private static bool LerBool(PluginManager pm, string propriedade)
        {
            if (string.IsNullOrWhiteSpace(propriedade))
                return false;

            try
            {
                object valor = pm.GetPropertyValue(propriedade.Trim());
                if (valor == null && !propriedade.StartsWith("DataCorePlugin.", StringComparison.Ordinal))
                    valor = pm.GetPropertyValue("DataCorePlugin." + propriedade.Trim());

                switch (valor)
                {
                    case null: return false;
                    case bool b: return b;
                    case string texto:
                        if (bool.TryParse(texto, out bool tb)) return tb;
                        return double.TryParse(texto, NumberStyles.Any, CultureInfo.InvariantCulture, out double td) && td != 0;
                    case IConvertible c: return Convert.ToDouble(c, CultureInfo.InvariantCulture) != 0;
                    default: return false;
                }
            }
            catch
            {
                return false;
            }
        }
    }

    internal static class Icone
    {
        private static ImageSource cache;

        public static ImageSource Criar()
        {
            if (cache != null)
                return cache;

            var grupo = new DrawingGroup();
            grupo.Children.Add(new GeometryDrawing(Brushes.Transparent, null, new RectangleGeometry(new Rect(0, 0, 32, 32))));
            grupo.Children.Add(new GeometryDrawing(null, new Pen(new SolidColorBrush(Color.FromRgb(200, 200, 200)), 2),
                new RectangleGeometry(new Rect(3, 8, 26, 16), 3, 3)));
            var leds = new[] { (9.0, Colors.OrangeRed), (16.0, Colors.Gold), (23.0, Colors.LimeGreen) };
            foreach (var (x, cor) in leds)
                grupo.Children.Add(new GeometryDrawing(new SolidColorBrush(cor), null, new EllipseGeometry(new Point(x, 16), 2.8, 2.8)));

            var imagem = new DrawingImage(grupo);
            imagem.Freeze();
            return cache = imagem;
        }
    }
}
