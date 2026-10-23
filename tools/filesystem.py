"""
NEO AI - Filesystem Automation Tools
Provides robust, validated tools for folder creation, file discovery,
directory inspection, and safe manipulation with post-condition verification.
"""

import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from core.safety import is_path_safe_for_deletion


def safe_path(path: str) -> Path:
    """Expands user path and resolves symlinks to an absolute Path."""
    return Path(path).expanduser().resolve()


SPECIAL_FOLDERS = {
    "downloads": lambda: Path.home() / "Downloads",
    "download": lambda: Path.home() / "Downloads",
    "documents": lambda: Path.home() / "Documents",
    "document": lambda: Path.home() / "Documents",
    "desktop": lambda: Path.home() / "Desktop",
    "pictures": lambda: Path.home() / "Pictures",
    "photos": lambda: Path.home() / "Pictures",
    "videos": lambda: Path.home() / "Videos",
    "music": lambda: Path.home() / "Music",
    "home": lambda: Path.home(),
    "user": lambda: Path.home(),
}


def open_special_folder(folder_name: str) -> str:
    """Opens a standard Windows user directory in File Explorer."""
    name = str(folder_name).lower().strip()
    resolver = SPECIAL_FOLDERS.get(name)
    if not resolver:
        # Fallback to general open_path
        return open_path(folder_name)

    folder = resolver()
    if not folder.exists():
        folder.mkdir(parents=True, exist_ok=True)

    try:
        os.startfile(str(folder))
        return f"Opened the {folder.name} folder ({folder})."
    except Exception as exc:
        return f"Could not open {name} folder: {exc}"


def create_folder(path: str) -> str:
    """Creates a directory at the given path and verifies its existence."""
    folder = safe_path(path)
    try:
        folder.mkdir(parents=True, exist_ok=True)
        if folder.is_dir():
            return f"Folder created successfully: {folder}"
        return f"Failed to verify folder creation at {folder}"
    except Exception as exc:
        return f"Could not create folder: {exc}"


def open_path(path: str) -> str:
    """Opens a file or directory using the default Windows application."""
    target = safe_path(path)
    if not target.exists():
        return f"Path does not exist: {target}"

    try:
        os.startfile(str(target))
        return f"Opened {target.name}."
    except Exception as exc:
        return f"Could not open {target.name}: {exc}"


def list_directory(path: str = ".") -> str:
    """Lists contents of a directory with DIR/FILE classifications and size."""
    directory = safe_path(path)
    if not directory.exists():
        return f"Directory does not exist: {directory}"

    if not directory.is_dir():
        return f"Not a directory: {directory}"

    try:
        items = []
        for item in sorted(directory.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            kind = "DIR " if item.is_dir() else "FILE"
            size_str = ""
            if item.is_file():
                try:
                    size = item.stat().st_size
                    if size < 1024:
                        size_str = f" ({size} B)"
                    elif size < 1024 * 1024:
                        size_str = f" ({size / 1024:.1f} KB)"
                    else:
                        size_str = f" ({size / (1024 * 1024):.1f} MB)"
                except Exception:
                    pass
            items.append(f"[{kind}] {item.name}{size_str}")

        if not items:
            return f"Directory '{directory.name}' is empty."

        return f"Contents of {directory}:\n" + "\n".join(items[:50])

    except PermissionError:
        return f"Access denied to directory: {directory}"
    except Exception as exc:
        return f"Error listing directory: {exc}"


def find_latest_file(extension: str = "pdf", directory: Optional[str] = None) -> str:
    """
    Finds the most recently modified file with the given extension.
    Searches standard user folders (Downloads, Documents, Desktop) if no directory is specified.
    """
    ext = extension.strip().lower().lstrip(".")
    search_dirs: List[Path] = []

    if directory:
        target = safe_path(directory)
        if target.is_dir():
            search_dirs.append(target)
    else:
        # Check standard user locations
        for d in [Path.home() / "Downloads", Path.home() / "Documents", Path.home() / "Desktop"]:
            if d.exists() and d.is_dir():
                search_dirs.append(d)

    if not search_dirs:
        return f"No valid search directories available to find .{ext} files."

    found_files: List[Tuple[float, Path]] = []

    for d in search_dirs:
        try:
            # Look top-level and 1 level down
            for pattern in [f"*.{ext}", f"*/*.{ext}"]:
                for file_path in d.glob(pattern):
                    if file_path.is_file():
                        try:
                            mtime = file_path.stat().st_mtime
                            found_files.append((mtime, file_path))
                        except Exception:
                            pass
        except Exception:
            continue

    if not found_files:
        return f"No .{ext.upper()} files were found in your recent folders (Downloads, Documents, Desktop)."

    # Sort descending by modification timestamp
    found_files.sort(key=lambda x: x[0], reverse=True)
    latest_mtime, latest_path = found_files[0]

    # Format human-friendly time and size
    try:
        mod_date = datetime.fromtimestamp(latest_mtime).strftime("%b %d, %Y at %I:%M %p")
        size_bytes = latest_path.stat().st_size
        if size_bytes < 1024 * 1024:
            size_str = f"{size_bytes / 1024:.1f} KB"
        else:
            size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
    except Exception:
        mod_date = "recently"
        size_str = "unknown size"

    return (
        f"Found latest {ext.upper()}: '{latest_path.name}'\n"
        f"Location: {latest_path.parent}\n"
        f"Size: {size_str} | Modified: {mod_date}"
    )


def find_files(query: str, extension: Optional[str] = None, directory: Optional[str] = None, limit: int = 5) -> str:
    """Finds files matching query substring and optional extension."""
    q = query.strip().lower()
    ext = extension.strip().lower().lstrip(".") if extension else None

    search_dirs = [safe_path(directory)] if directory else [
        Path.home() / "Downloads",
        Path.home() / "Documents",
        Path.home() / "Desktop"
    ]

    matches: List[Path] = []
    for d in search_dirs:
        if not d.exists() or not d.is_dir():
            continue
        try:
            for p in d.rglob("*"):
                if p.is_file():
                    if ext and p.suffix.lower().lstrip(".") != ext:
                        continue
                    if q in p.name.lower():
                        matches.append(p)
                        if len(matches) >= limit:
                            break
        except Exception:
            continue
        if len(matches) >= limit:
            break

    if not matches:
        return f"No files matching '{query}' were found."

    results = [f"Found {len(matches)} matching file(s):"]
    for m in matches:
        results.append(f"- {m.name} ({m.parent})")
    return "\n".join(results)


def move_file(source: str, destination: str) -> str:
    """Moves a file from source to destination and verifies completion."""
    src = safe_path(source)
    dst = safe_path(destination)

    if not src.exists():
        return f"Source file does not exist: {src}"

    if dst.is_dir():
        dst = dst / src.name

    if dst.exists():
        return f"Destination already exists: {dst}"

    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        if dst.exists():
            return f"Moved '{src.name}' to '{dst}'."
        return f"Failed to verify file move to {dst}"
    except Exception as exc:
        return f"Could not move file: {exc}"


def rename_file(source: str, destination: str) -> str:
    """Renames a file and verifies completion."""
    src = safe_path(source)
    dst = safe_path(destination)

    if not src.exists():
        return f"Source does not exist: {src}"

    if dst.exists():
        return f"Destination already exists: {dst}"

    try:
        src.rename(dst)
        if dst.exists():
            return f"Renamed '{src.name}' to '{dst.name}'."
        return f"Failed to verify rename to {dst.name}"
    except Exception as exc:
        return f"Could not rename file: {exc}"


def delete_path(path: str) -> str:
    """Permanently deletes a file or directory after safety checks."""
    # Validate the raw input before resolving it so traversal components are
    # not erased by Path.resolve(). Then validate the resolved target too, to
    # catch symlinks or aliases that point into protected locations.
    safe, reason = is_path_safe_for_deletion(str(path))
    if not safe:
        return f"Safety refusal: {reason}"

    target = safe_path(path)
    safe, reason = is_path_safe_for_deletion(str(target))
    if not safe:
        return f"Safety refusal: {reason}"

    if not target.exists():
        return f"Path does not exist: {target}"

    try:
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()

        # Verify removal
        if not target.exists():
            return f"Successfully deleted {target.name}."
        return f"Failed to verify deletion of {target}"
    except Exception as exc:
        return f"Could not delete path: {exc}"
