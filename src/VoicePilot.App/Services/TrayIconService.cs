using System.Drawing;
using System.Windows.Forms;

namespace VoicePilot.App.Services;

public class TrayIconService : IDisposable
{
    private readonly NotifyIcon _notifyIcon;
    private bool _isDisposed;

    public event Action? OpenRequested;
    public event Action? StartListeningRequested;
    public event Action? StopListeningRequested;
    public event Action? SettingsRequested;
    public event Action? ExitRequested;

    public TrayIconService()
    {
        _notifyIcon = new NotifyIcon
        {
            Text = "VoicePilot AI Desktop Voice Assistant",
            Visible = true,
            Icon = CreateGeneratedIcon()
        };

        var contextMenu = new ContextMenuStrip();
        contextMenu.Items.Add("Open VoicePilot", null, (_, _) => OpenRequested?.Invoke());
        contextMenu.Items.Add(new ToolStripSeparator());
        contextMenu.Items.Add("Start Listening", null, (_, _) => StartListeningRequested?.Invoke());
        contextMenu.Items.Add("Stop Listening", null, (_, _) => StopListeningRequested?.Invoke());
        contextMenu.Items.Add("Settings", null, (_, _) => SettingsRequested?.Invoke());
        contextMenu.Items.Add(new ToolStripSeparator());
        contextMenu.Items.Add("Exit", null, (_, _) => ExitRequested?.Invoke());

        _notifyIcon.ContextMenuStrip = contextMenu;
        _notifyIcon.DoubleClick += (_, _) => OpenRequested?.Invoke();
    }

    public void ShowNotification(string title, string message, ToolTipIcon icon = ToolTipIcon.Info)
    {
        try
        {
            _notifyIcon.ShowBalloonTip(3000, title, message, icon);
        }
        catch { }
    }

    private static Icon CreateGeneratedIcon()
    {
        // Generates an elegant 32x32 tray icon with cyan/violet orb
        using var bmp = new Bitmap(32, 32);
        using var g = Graphics.FromImage(bmp);
        g.SmoothingMode = System.Drawing.Drawing2D.SmoothingMode.AntiAlias;

        // Vibrant gradient background orb
        using var brush = new System.Drawing.Drawing2D.LinearGradientBrush(
            new Rectangle(2, 2, 28, 28),
            Color.FromArgb(0, 210, 255),
            Color.FromArgb(155, 81, 224),
            45f);

        g.FillEllipse(brush, 2, 2, 28, 28);

        // Center mic symbol
        using var whiteBrush = new SolidBrush(Color.White);
        g.FillRoundedRectangle(whiteBrush, 12, 8, 8, 12, 4);
        using var pen = new Pen(Color.White, 2);
        g.DrawArc(pen, 9, 12, 14, 10, 0, 180);
        g.DrawLine(pen, 16, 22, 16, 26);
        g.DrawLine(pen, 12, 26, 20, 26);

        return Icon.FromHandle(bmp.GetHicon());
    }

    public void Dispose()
    {
        if (_isDisposed)
            return;
        _isDisposed = true;

        _notifyIcon.Visible = false;
        _notifyIcon.Dispose();
        GC.SuppressFinalize(this);
    }
}

internal static class GraphicsExtensions
{
    public static void FillRoundedRectangle(this Graphics g, Brush brush, int x, int y, int width, int height, int radius)
    {
        using var path = new System.Drawing.Drawing2D.GraphicsPath();
        path.AddArc(x, y, radius * 2, radius * 2, 180, 90);
        path.AddArc(x + width - 2 * radius, y, radius * 2, radius * 2, 270, 90);
        path.AddArc(x + width - 2 * radius, y + height - 2 * radius, radius * 2, radius * 2, 0, 90);
        path.AddArc(x, y + height - 2 * radius, radius * 2, radius * 2, 90, 90);
        path.CloseFigure();
        g.FillPath(brush, path);
    }
}
