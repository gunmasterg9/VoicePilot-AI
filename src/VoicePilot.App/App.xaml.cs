using System.Windows;
using Microsoft.Extensions.DependencyInjection;
using VoicePilot.App.Services;
using VoicePilot.App.ViewModels;
using VoicePilot.App.Views;
using VoicePilot.Core;
using VoicePilot.Core.Configuration;
using VoicePilot.Core.Plugins;
using VoicePilot.Core.Security;
using VoicePilot.Plugins.Sample;

namespace VoicePilot.App;

public partial class App : System.Windows.Application
{
    private ServiceProvider? _serviceProvider;

    protected override async void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);

        AppDomain.CurrentDomain.UnhandledException += (_, args) =>
        {
            var ex = args.ExceptionObject as Exception;
            System.Diagnostics.Debug.WriteLine($"[CRITICAL] Unhandled domain exception: {SensitiveDataMasker.Mask(ex?.ToString() ?? "")}");
        };

        var services = new ServiceCollection();
        ConfigureServices(services);
        _serviceProvider = services.BuildServiceProvider();

        // Initialize plugin loader & register sample plugin
        var pluginLoader = _serviceProvider.GetRequiredService<PluginLoader>();
        pluginLoader.RegisterPluginInstance(new SampleUtilityPlugin());
        await pluginLoader.DiscoverAndLoadPluginsAsync();

        // Launch MainWindow
        var mainWindow = _serviceProvider.GetRequiredService<MainWindow>();
        MainWindow = mainWindow;

        var settings = _serviceProvider.GetRequiredService<SettingsManager>().Current;
        if (!settings.StartMinimized)
        {
            mainWindow.Show();
        }
    }

    private void ConfigureServices(IServiceCollection services)
    {
        // 1. VoicePilot Core Services
        services.AddVoicePilotCore();

        // 2. Windows Services
        services.AddSingleton<GlobalHotkeyService>();
        services.AddSingleton<TrayIconService>();

        // 3. ViewModels
        services.AddTransient<SettingsViewModel>();
        services.AddSingleton<MainViewModel>(sp =>
        {
            var engine = sp.GetRequiredService<AssistantEngine>();
            var settingsVmFactory = () => sp.GetRequiredService<SettingsViewModel>();
            var openSettings = (SettingsViewModel vm) =>
            {
                var win = new SettingsWindow(vm)
                {
                    Owner = System.Windows.Application.Current.MainWindow
                };
                win.ShowDialog();
            };

            return new MainViewModel(engine, settingsVmFactory, openSettings);
        });

        // 4. Windows
        services.AddSingleton<MainWindow>();
    }

    protected override void OnExit(ExitEventArgs e)
    {
        _serviceProvider?.Dispose();
        base.OnExit(e);
    }
}
