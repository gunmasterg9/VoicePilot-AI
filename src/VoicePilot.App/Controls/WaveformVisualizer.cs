using System.Windows;
using System.Windows.Media;

namespace VoicePilot.App.Controls;

/// <summary>
/// Native WPF visualizer control that renders a lively animated audio waveform
/// responding smoothly to real-time microphone volume levels.
/// </summary>
public class WaveformVisualizer : FrameworkElement
{
    private readonly Random _random = new(42);
    private double _phase;
    private readonly CompositionTargetRenderingHelper _renderingHelper;

    public static readonly DependencyProperty AudioLevelProperty =
        DependencyProperty.Register(
            nameof(AudioLevel),
            typeof(float),
            typeof(WaveformVisualizer),
            new FrameworkPropertyMetadata(0.0f, FrameworkPropertyMetadataOptions.AffectsRender));

    public static readonly DependencyProperty IsListeningProperty =
        DependencyProperty.Register(
            nameof(IsListening),
            typeof(bool),
            typeof(WaveformVisualizer),
            new FrameworkPropertyMetadata(false, FrameworkPropertyMetadataOptions.AffectsRender));

    public float AudioLevel
    {
        get => (float)GetValue(AudioLevelProperty);
        set => SetValue(AudioLevelProperty, value);
    }

    public bool IsListening
    {
        get => (bool)GetValue(IsListeningProperty);
        set => SetValue(IsListeningProperty, value);
    }

    public WaveformVisualizer()
    {
        _renderingHelper = new CompositionTargetRenderingHelper(OnRenderFrame);
        Loaded += (_, _) => _renderingHelper.Start();
        Unloaded += (_, _) => _renderingHelper.Stop();
    }

    private void OnRenderFrame()
    {
        _phase += IsListening ? 0.12 : 0.04;
        if (_phase > Math.PI * 2)
            _phase -= Math.PI * 2;

        InvalidateVisual();
    }

    protected override void OnRender(DrawingContext dc)
    {
        base.OnRender(dc);

        var w = ActualWidth;
        var h = ActualHeight;
        if (w <= 0 || h <= 0)
            return;

        const int barCount = 28;
        var barSpacing = 4.0;
        var totalSpacing = barSpacing * (barCount - 1);
        var barWidth = Math.Max(2.0, (w - totalSpacing) / barCount);
        var midY = h / 2.0;

        // Gradient for vibrant animated sound bars
        var brush = new LinearGradientBrush(
            System.Windows.Media.Color.FromRgb(0, 210, 255), // Cyan
            System.Windows.Media.Color.FromRgb(155, 81, 224), // Violet
            new System.Windows.Point(0, 1),
            new System.Windows.Point(0, 0));

        var idleBrush = new SolidColorBrush(System.Windows.Media.Color.FromArgb(60, 100, 140, 200));

        var currentLevel = Math.Clamp(AudioLevel, 0.0f, 1.0f);

        for (int i = 0; i < barCount; i++)
        {
            var x = i * (barWidth + barSpacing);
            var normalizedX = (double)i / barCount;

            // Bell curve envelope so bars are taller in the center
            var envelope = Math.Sin(normalizedX * Math.PI);

            double targetHeight;
            if (IsListening)
            {
                var wave = Math.Sin(_phase + (i * 0.45));
                var randomJitter = (_random.NextDouble() * 0.25);
                var amplitude = Math.Max(0.12, (currentLevel * 1.8) + (wave * 0.15) + randomJitter);
                targetHeight = Math.Max(4.0, amplitude * (h * 0.85) * envelope);
            }
            else
            {
                // Subtle ambient pulse when idle
                var wave = Math.Sin(_phase + (i * 0.3));
                targetHeight = Math.Max(3.0, (6.0 + (wave * 4.0)) * envelope);
            }

            var y = midY - (targetHeight / 2.0);
            var rect = new Rect(x, y, barWidth, targetHeight);

            dc.DrawRoundedRectangle(
                IsListening ? brush : idleBrush,
                null,
                rect,
                barWidth / 2.0,
                barWidth / 2.0);
        }
    }

    private class CompositionTargetRenderingHelper
    {
        private readonly Action _callback;
        private bool _isRunning;

        public CompositionTargetRenderingHelper(Action callback)
        {
            _callback = callback;
        }

        public void Start()
        {
            if (!_isRunning)
            {
                CompositionTarget.Rendering += OnRendering;
                _isRunning = true;
            }
        }

        public void Stop()
        {
            if (_isRunning)
            {
                CompositionTarget.Rendering -= OnRendering;
                _isRunning = false;
            }
        }

        private void OnRendering(object? sender, EventArgs e)
        {
            _callback();
        }
    }
}
