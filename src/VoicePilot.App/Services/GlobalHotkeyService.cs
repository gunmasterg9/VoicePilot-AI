using System.Windows;
using System.Windows.Interop;
using VoicePilot.Core.Interop;

namespace VoicePilot.App.Services;

public class GlobalHotkeyService : IDisposable
{
    private const int HotkeyId = 9001;
    private IntPtr _windowHandle = IntPtr.Zero;
    private HwndSource? _hwndSource;
    private bool _isRegistered;

    public event Action? HotkeyPressed;

    public bool Register(Window window, string hotkeyString = "Ctrl+Win+Space")
    {
        Unregister();

        _windowHandle = new WindowInteropHelper(window).EnsureHandle();
        _hwndSource = HwndSource.FromHwnd(_windowHandle);
        _hwndSource?.AddHook(HwndHook);

        ParseHotkey(hotkeyString, out var modifiers, out var vk);

        _isRegistered = NativeMethods.RegisterHotKey(_windowHandle, HotkeyId, (uint)modifiers, (uint)vk);
        return _isRegistered;
    }

    public void Unregister()
    {
        if (_isRegistered && _windowHandle != IntPtr.Zero)
        {
            NativeMethods.UnregisterHotKey(_windowHandle, HotkeyId);
            _isRegistered = false;
        }

        if (_hwndSource != null)
        {
            _hwndSource.RemoveHook(HwndHook);
            _hwndSource = null;
        }
    }

    private IntPtr HwndHook(IntPtr hwnd, int msg, IntPtr wParam, IntPtr lParam, ref bool handled)
    {
        if (msg == NativeMethods.WM_HOTKEY && wParam.ToInt32() == HotkeyId)
        {
            HotkeyPressed?.Invoke();
            handled = true;
        }
        return IntPtr.Zero;
    }

    private static void ParseHotkey(string hotkey, out NativeMethods.KeyModifiers modifiers, out int vk)
    {
        modifiers = NativeMethods.KeyModifiers.NoRepeat;
        vk = 0x20; // Default VK_SPACE (32)

        var parts = hotkey.Split('+', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
        foreach (var part in parts)
        {
            var p = part.ToLowerInvariant();
            if (p.Contains("ctrl") || p.Contains("control"))
                modifiers |= NativeMethods.KeyModifiers.Control;
            else if (p.Contains("win") || p.Contains("windows"))
                modifiers |= NativeMethods.KeyModifiers.Windows;
            else if (p.Contains("alt"))
                modifiers |= NativeMethods.KeyModifiers.Alt;
            else if (p.Contains("shift"))
                modifiers |= NativeMethods.KeyModifiers.Shift;
            else if (p == "space")
                vk = 0x20;
            else if (p == "v")
                vk = 0x56;
            else if (p == "m")
                vk = 0x4D;
            else if (p.Length == 1 && char.IsLetterOrDigit(p[0]))
                vk = char.ToUpperInvariant(p[0]);
        }
    }

    public void Dispose()
    {
        Unregister();
        GC.SuppressFinalize(this);
    }
}
