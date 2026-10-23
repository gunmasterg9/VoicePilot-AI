"""
NEO AI - System Management and Telemetry Tools
Provides PC power controls, locking, and system resource inspections.
"""

import subprocess
import psutil
from typing import Dict, Any


def get_ram_info() -> str:
    """Returns available and used system RAM statistics."""
    try:
        mem = psutil.virtual_memory()
        total_gb = round(mem.total / (1024**3), 1)
        available_gb = round(mem.available / (1024**3), 1)
        used_gb = round((mem.total - mem.available) / (1024**3), 1)
        percent = mem.percent
        return (
            f"RAM telemetry: {available_gb} GB available out of {total_gb} GB total "
            f"({used_gb} GB used, {percent}% load)."
        )
    except Exception as exc:
        return f"Could not read memory telemetry: {exc}"


def get_system_telemetry(category: str = "all") -> str:
    """Inspects CPU, RAM, battery, and disk resources."""
    try:
        cat = category.lower().strip()
        parts = []

        if cat in {"all", "ram", "memory"}:
            mem = psutil.virtual_memory()
            avail_gb = round(mem.available / (1024**3), 1)
            total_gb = round(mem.total / (1024**3), 1)
            parts.append(f"RAM: {mem.percent}% used ({avail_gb} GB available of {total_gb} GB)")

        if cat in {"all", "cpu"}:
            cpu = psutil.cpu_percent(interval=0.1)
            cores = psutil.cpu_count(logical=True)
            parts.append(f"CPU: {cpu}% across {cores} logical cores")

        if cat in {"all", "battery"}:
            batt = psutil.sensors_battery()
            if batt:
                plugged = "Plugged in" if batt.power_plugged else "On battery"
                parts.append(f"Battery: {batt.percent}% ({plugged})")
            else:
                parts.append("Power: AC power connected")

        if cat in {"all", "disk"}:
            disk = psutil.disk_usage("C:\\")
            free_gb = round(disk.free / (1024**3), 1)
            total_gb = round(disk.total / (1024**3), 1)
            parts.append(f"Disk (C:): {free_gb} GB free of {total_gb} GB ({disk.percent}% used)")

        return " | ".join(parts)
    except Exception as exc:
        return f"Could not gather system telemetry: {exc}"


def lock_pc() -> str:
    """Locks the current Windows user session."""
    subprocess.Popen(
        ["rundll32.exe", "user32.dll,LockWorkStation"]
    )
    return "PC locked."


def shutdown_pc(delay: int = 5) -> str:
    """Schedules a Windows shutdown."""
    subprocess.Popen(
        ["shutdown", "/s", "/t", str(int(delay))]
    )
    return f"Shutdown scheduled in {delay} seconds."


def restart_pc(delay: int = 5) -> str:
    """Schedules a Windows system restart."""
    subprocess.Popen(
        ["shutdown", "/r", "/t", str(int(delay))]
    )
    return f"Restart scheduled in {delay} seconds."


def cancel_shutdown() -> str:
    """Cancels any pending shutdown or restart."""
    subprocess.Popen(
        ["shutdown", "/a"]
    )
    return "Pending shutdown or restart cancelled."
