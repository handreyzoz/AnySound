using System;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Threading;

namespace ButtonBoxETS2
{
    /// <summary>Tela do plugin no menu esquerdo do SimHub (montada em código, sem XAML).</summary>
    public class SettingsControl : UserControl
    {
        private const string Formula = "[ButtonBoxPlugin.Mensagem]";

        private readonly ButtonBoxPlugin plugin;
        private readonly TextBlock txtStatus;
        private readonly TextBlock txtMensagem;
        private readonly TextBlock txtErro;
        private readonly DispatcherTimer timer;

        private ButtonBoxSettings S => plugin.Settings;

        public SettingsControl(ButtonBoxPlugin plugin)
        {
            this.plugin = plugin;

            var raiz = new StackPanel { Margin = new Thickness(12), MaxWidth = 760, HorizontalAlignment = HorizontalAlignment.Left };

            raiz.Children.Add(new TextBlock { Text = "Button Box ETS2", FontSize = 22, FontWeight = FontWeights.Bold, Margin = new Thickness(0, 0, 0, 4) });
            raiz.Children.Add(Texto("Pino 16 = LEDs WS2812B (perfil de LEDs) · Pino 9 = botão do SimHub. Esses pinos ficam fora desta tela."));

            txtErro = new TextBlock { Foreground = Brushes.OrangeRed, FontWeight = FontWeights.Bold, TextWrapping = TextWrapping.Wrap, Margin = new Thickness(0, 6, 0, 0) };
            raiz.Children.Add(txtErro);

            // Estado ao vivo
            txtStatus = new TextBlock { FontFamily = new FontFamily("Consolas"), TextWrapping = TextWrapping.Wrap };
            txtMensagem = new TextBlock { FontFamily = new FontFamily("Consolas"), Opacity = 0.7, Margin = new Thickness(0, 4, 0, 0) };
            raiz.Children.Add(Grupo("Estado ao vivo", txtStatus, txtMensagem));

            // Pisca-alerta
            raiz.Children.Add(Grupo("Relé do pisca-alerta",
                Check("Ativado", S.AlertaAtivo, v => S.AlertaAtivo = v),
                Linha("Pino do relé", ComboPino(S.PinoPisca, v => S.PinoPisca = v)),
                Linha("Comportamento", Combo(new[]
                {
                    "Contínuo: ligado enquanto o alerta estiver ativo",
                    "Sincronizado: liga e desliga junto com o pisca do jogo",
                    "Original: ligado nos intervalos do pisca (código antigo)",
                }, S.ModoAlerta, v => S.ModoAlerta = v)),
                Linha("Teste", ComboTeste(plugin.TesteAlerta, v => plugin.TesteAlerta = v))));

            // Meia-luz
            raiz.Children.Add(Grupo("Relé da meia-luz",
                Check("Ativado", S.MeiaLuzAtiva, v => S.MeiaLuzAtiva = v),
                Linha("Pino do relé", ComboPino(S.PinoMeiaLuz, v => S.PinoMeiaLuz = v)),
                Linha("Teste", ComboTeste(plugin.TesteMeiaLuz, v => plugin.TesteMeiaLuz = v))));

            raiz.Children.Add(Grupo("Módulo de relés",
                Check("Relé liga com LOW (a maioria dos módulos de relé)", S.ReleAtivoEmLow, v => S.ReleAtivoEmLow = v)));

            // Botão do Kadett
            raiz.Children.Add(Grupo("Botão / chave do Kadett",
                Linha("Pino (ligado ao GND)", ComboPino(S.PinoBotao, v => S.PinoBotao = v)),
                Linha("Botão do gamepad", Numero(S.BotaoGamepad, v => S.BotaoGamepad = v)),
                Linha("Funcionamento", Combo(new[]
                {
                    "Pulso a cada mudança (chave liga/desliga)",
                    "Pulso só ao apertar (botão de pressão)",
                    "Segue o estado (apertado = botão pressionado)",
                }, S.ModoBotao, v => S.ModoBotao = v)),
                Linha("Duração do pulso (ms)", Numero(S.PulsoMs, v => S.PulsoMs = v)),
                Texto("No ETS2: Opções → Controles → Pisca-alerta → aperte o botão/chave.")));

            // Fórmula
            var copiar = new Button { Content = "Copiar fórmula", Padding = new Thickness(10, 3, 10, 3), Margin = new Thickness(0, 6, 0, 0), HorizontalAlignment = HorizontalAlignment.Left };
            copiar.Click += (o, e) => Clipboard.SetText(Formula);
            raiz.Children.Add(Grupo("Ligação com o Arduino",
                Texto("SimHub → Arduino → My hardware → Custom Protocol. Use esta fórmula (NCalc):"),
                new TextBox { Text = Formula, IsReadOnly = true, FontFamily = new FontFamily("Consolas"), Margin = new Thickness(0, 4, 0, 0) },
                copiar));

            // Avançado
            var avancado = new Expander
            {
                Header = "Avançado",
                Margin = new Thickness(0, 8, 0, 0),
                Content = new StackPanel
                {
                    Margin = new Thickness(8),
                    Children =
                    {
                        Check("Só funcionar no ETS2/ATS", S.SomenteETS2ATS, v => S.SomenteETS2ATS = v),
                        Linha("Pisca-alerta", Propriedade(S.PropAlerta, v => S.PropAlerta = v)),
                        Linha("Seta esquerda", Propriedade(S.PropSetaEsquerda, v => S.PropSetaEsquerda = v)),
                        Linha("Seta direita", Propriedade(S.PropSetaDireita, v => S.PropSetaDireita = v)),
                        Linha("Meia-luz", Propriedade(S.PropMeiaLuz, v => S.PropMeiaLuz = v)),
                    },
                },
            };
            raiz.Children.Add(avancado);

            Content = new ScrollViewer { VerticalScrollBarVisibility = ScrollBarVisibility.Auto, Content = raiz };

            timer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(200) };
            timer.Tick += (o, e) => AtualizarStatus();
            Loaded += (o, e) => timer.Start();
            Unloaded += (o, e) => timer.Stop();

            MostrarErro();
        }

        private void AtualizarStatus()
        {
            string Estado(bool v) => v ? "LIGADO   " : "desligado";
            txtStatus.Text =
                $"Jogo:        {(plugin.JogoAtivo ? "rodando" : "parado")}\n" +
                $"Alerta jogo: {Estado(plugin.AlertaNoJogo)}  →  relé pino {S.PinoPisca}: {Estado(plugin.AlertaSaida)}\n" +
                $"Meia-luz:    {Estado(plugin.MeiaLuzNoJogo)}  →  relé pino {S.PinoMeiaLuz}: {Estado(plugin.MeiaLuzSaida)}";
            txtMensagem.Text = "Enviando: " + plugin.Mensagem.TrimEnd('\n');
        }

        private void Alterado()
        {
            plugin.AtualizarConfiguracao();
            plugin.Salvar();
            MostrarErro();
        }

        private void MostrarErro()
        {
            txtErro.Text = plugin.ErroConfiguracao == null
                ? ""
                : "⚠ " + plugin.ErroConfiguracao + " A configuração anterior continua no Arduino até corrigir.";
        }

        // ---------- Construtores de controles ----------

        private static TextBlock Texto(string texto) =>
            new TextBlock { Text = texto, TextWrapping = TextWrapping.Wrap, Opacity = 0.8, Margin = new Thickness(0, 2, 0, 2) };

        private static GroupBox Grupo(string titulo, params UIElement[] filhos)
        {
            var painel = new StackPanel { Margin = new Thickness(6) };
            foreach (var f in filhos)
                painel.Children.Add(f);
            return new GroupBox { Header = titulo, Content = painel, Margin = new Thickness(0, 8, 0, 0) };
        }

        private static UIElement Linha(string rotulo, FrameworkElement controle)
        {
            var grid = new Grid { Margin = new Thickness(0, 3, 0, 3) };
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(170) });
            grid.ColumnDefinitions.Add(new ColumnDefinition());
            var label = new TextBlock { Text = rotulo, VerticalAlignment = VerticalAlignment.Center };
            Grid.SetColumn(controle, 1);
            grid.Children.Add(label);
            grid.Children.Add(controle);
            return grid;
        }

        private CheckBox Check(string texto, bool valor, Action<bool> salvar)
        {
            var c = new CheckBox { Content = texto, IsChecked = valor, Margin = new Thickness(0, 3, 0, 3) };
            c.Click += (o, e) => { salvar(c.IsChecked == true); Alterado(); };
            return c;
        }

        private ComboBox Combo(string[] opcoes, int valor, Action<int> salvar)
        {
            var c = new ComboBox { ItemsSource = opcoes, SelectedIndex = Math.Max(0, Math.Min(valor, opcoes.Length - 1)) };
            c.SelectionChanged += (o, e) => { salvar(c.SelectedIndex); Alterado(); };
            return c;
        }

        private ComboBox ComboPino(int valor, Action<int> salvar)
        {
            var pinos = ButtonBoxPlugin.PinosLivres.ToList();
            if (!pinos.Contains(valor))
                pinos.Insert(0, valor);
            var c = new ComboBox { ItemsSource = pinos, SelectedItem = valor, Width = 90, HorizontalAlignment = HorizontalAlignment.Left };
            c.SelectionChanged += (o, e) => { if (c.SelectedItem is int p) { salvar(p); Alterado(); } };
            return c;
        }

        private static ComboBox ComboTeste(int valor, Action<int> salvar)
        {
            var c = new ComboBox
            {
                ItemsSource = new[] { "Automático (segue o jogo)", "Forçar LIGADO", "Forçar DESLIGADO" },
                SelectedIndex = valor,
            };
            // Teste não é salvo: ao reiniciar o SimHub volta para automático
            c.SelectionChanged += (o, e) => salvar(c.SelectedIndex);
            return c;
        }

        private TextBox Numero(int valor, Action<int> salvar)
        {
            var t = new TextBox { Text = valor.ToString(), Width = 90, HorizontalAlignment = HorizontalAlignment.Left };
            t.TextChanged += (o, e) => { if (int.TryParse(t.Text, out int n)) { salvar(n); Alterado(); } };
            return t;
        }

        private TextBox Propriedade(string valor, Action<string> salvar)
        {
            var t = new TextBox { Text = valor, FontFamily = new FontFamily("Consolas") };
            t.LostFocus += (o, e) => { salvar(t.Text.Trim()); Alterado(); };
            return t;
        }
    }
}
