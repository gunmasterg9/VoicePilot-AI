using System.ComponentModel;
using System.Collections.Specialized;
using System.Windows;
using System.Windows.Input;
using VoicePilot.App.Services;
using VoicePilot.App.ViewModels;
using VoicePilot.Core.Configuration;

namespace VoicePilot.App.Views;

public partial class MainWindow : Window
{
    private readonly MainViewModel _viewModel;
    private readonly GlobalHotkeyService _hotkeyService;
    private readonly TrayIconService _trayIconService;
    private readonly SettingsManager _settingsManager;
    private bool _isExplicitExit;

    public MainWindow(
        MainViewModel viewModel,
        GlobalHotkeyService hotkeyService,
        TrayIconService trayIconService,
        SettingsManager settingsManager)
    {
        InitializeComponent();
        _viewModel = viewModel;
        _hotkeyService = hotkeyService;
        _trayIconService = trayIconService;
        _settingsManager = settingsManager;

        DataContext = _viewModel;

        SourceInitialized += OnSourceInitialized;
        Closing += OnWindowClosing;

        // Auto-scroll conversation feed
        ((INotifyCollectionChanged)_viewModel.Conversation).CollectionChanged += (_, _) =>
        {
            Dispatcher.InvokeAsync(() => ChatScrollViewer.ScrollToEnd());
        };

        // Wire tray icon events
        _trayIconService.OpenRequested += RestoreAndActivate;
        _trayIconService.StartListeningRequested += () => Dispatcher.InvokeAsync(() =>
        {
            RestoreAndActivate();
            if (!_viewModel.IsListening)
                _viewModel.ToggleListeningCommand.Execute(null);
        });
        _trayIconService.StopListeningRequested += () => Dispatcher.InvokeAsync(() =>
        {
            if (_viewModel.IsListening)
                _viewModel.ToggleListeningCommand.Execute(null);
        });
        _trayIconService.SettingsRequested += () => Dispatcher.InvokeAsync(() =>
        {
            RestoreAndActivate();
            _viewModel.OpenSettingsCommand.Execute(null);
        });
        _trayIconService.ExitRequested += () => Dispatcher.Invoke(() =>
        {
            _isExplicitExit = true;
            Close();
            System.Windows.Application.Current.Shutdown();
        });
    }

    private void OnSourceInitialized(object? sender, EventArgs e)
    {
        // Register global hotkey
        var hotkey = _settingsManager.Current.GlobalHotkey;
        _hotkeyService.Register(this, hotkey);
        _hotkeyService.HotkeyPressed += OnGlobalHotkeyPressed;
    }

    private void OnGlobalHotkeyPressed()
    {
        Dispatcher.Invoke(() =>
        {
            RestoreAndActivate();
            _viewModel.ToggleListeningCommand.Execute(null);
        });
    }

    public void RestoreAndActivate()
    {
        Show();
        if (WindowState == WindowState.Minimized)
        {
            WindowState = WindowState.Normal;
        }
        Activate();
        Focus();
    }

    private void OnWindowClosing(object? sender, CancelEventArgs e)
    {
        if (_isExplicitExit)
            return;

        if (_settingsManager.Current.MinimizeToTrayOnClose)
        {
            e.Cancel = true;
            Hide();
            _trayIconService.ShowNotification(
                "VoicePilot AI Running in Background",
                $"Press {_settingsManager.Current.GlobalHotkey} or click the tray icon anytime to speak.");
        }
    }

    private void OnTextInputKeyDown(object sender, System.Windows.Input.KeyEventArgs e)
    {
        if (e.Key == Key.Enter)
        {
            if (_viewModel.SendTextCommand.CanExecute(null))
            {
                _viewModel.SendTextCommand.Execute(null);
            }
        }
    }

    protected override void OnClosed(EventArgs e)
    {
        _hotkeyService.Dispose();
        _trayIconService.Dispose();
        base.OnClosed(e);
    }
}
