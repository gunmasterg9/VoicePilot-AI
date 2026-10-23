
import subprocess


def lock_pc():

    subprocess.Popen(
        [
            "rundll32.exe",
            "user32.dll,LockWorkStation"
        ]
    )

    return "PC locked."


def shutdown_pc(delay=5):

    subprocess.Popen(
        [
            "shutdown",
            "/s",
            "/t",
            str(int(delay))
        ]
    )

    return "Shutdown scheduled."


def restart_pc(delay=5):

    subprocess.Popen(
        [
            "shutdown",
            "/r",
            "/t",
            str(int(delay))
        ]
    )

    return "Restart scheduled."


def cancel_shutdown():

    subprocess.Popen(
        [
            "shutdown",
            "/a"
        ]
    )

    return (
        "Pending shutdown or restart cancelled."
    )
