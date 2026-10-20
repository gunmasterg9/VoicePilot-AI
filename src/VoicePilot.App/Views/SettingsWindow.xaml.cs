using System.Windows;
using VoicePilot.App.ViewModels;

namespace VoicePilot.App.Views;

public partial class SettingsWindow : Window
{
    public SettingsWindow(SettingsViewModel viewModel)
    {
        InitializeComponent();
        DataContext = viewModel;
        viewModel.RequestClose += () => Close();
    }

    private void OnCancelClick(object sender, RoutedEventArgs e)
    {
        Close();
    }
}
