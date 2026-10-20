using System.Runtime.InteropServices;

namespace VoicePilot.Core.Interop;

/// <summary>
/// Supported Win32 API definitions and P/Invoke signatures for Windows desktop integration.
/// </summary>
public static class NativeMethods
{
    public const int WM_HOTKEY = 0x0312;

    [Flags]
    public enum KeyModifiers : uint
    {
        None = 0,
        Alt = 1,
        Control = 2,
        Shift = 4,
        Windows = 8,
        NoRepeat = 0x4000
    }

    [DllImport("user32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool RegisterHotKey(IntPtr hWnd, int id, uint fsModifiers, uint vk);

    [DllImport("user32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool UnregisterHotKey(IntPtr hWnd, int id);

    [DllImport("user32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool LockWorkStation();

    [DllImport("user32.dll", CharSet = CharSet.Auto)]
    public static extern IntPtr SendMessage(IntPtr hWnd, int msg, IntPtr wParam, IntPtr lParam);

    public const int WM_APPCOMMAND = 0x0319;
    public const int APPCOMMAND_VOLUME_MUTE = 0x80000;
    public const int APPCOMMAND_VOLUME_DOWN = 0x90000;
    public const int APPCOMMAND_VOLUME_UP = 0xA0000;
}
