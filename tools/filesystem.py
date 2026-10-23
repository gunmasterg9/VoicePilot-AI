
from pathlib import Path
import shutil


def safe_path(path):

    return (
        Path(path)
        .expanduser()
        .resolve()
    )


def create_folder(path):

    folder = safe_path(path)

    folder.mkdir(
        parents=True,
        exist_ok=True
    )

    return (
        f"Folder created: {folder}"
    )


def open_path(path):

    import os

    target = safe_path(path)

    if not target.exists():

        return (
            f"Path does not exist: {target}"
        )

    os.startfile(
        str(target)
    )

    return (
        f"Opened {target}"
    )


def list_directory(path="."):

    directory = safe_path(path)

    if not directory.exists():

        return (
            f"Directory does not exist: {directory}"
        )

    if not directory.is_dir():

        return (
            f"Not a directory: {directory}"
        )

    try:

        items = []

        for item in directory.iterdir():

            kind = (
                "DIR"
                if item.is_dir()
                else "FILE"
            )

            items.append(
                f"[{kind}] {item.name}"
            )

        if not items:
            return "The directory is empty."

        return "\n".join(items)

    except PermissionError:

        return "Permission denied."


def move_file(
    source,
    destination
):

    source = safe_path(source)
    destination = safe_path(destination)

    if not source.exists():

        return (
            f"Source does not exist: {source}"
        )

    if destination.exists():

        return (
            f"Destination already exists: {destination}"
        )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    shutil.move(
        str(source),
        str(destination)
    )

    return (
        f"Moved {source.name} to {destination}"
    )


def rename_file(
    source,
    destination
):

    source = safe_path(source)
    destination = safe_path(destination)

    if not source.exists():

        return (
            f"Source does not exist: {source}"
        )

    if destination.exists():

        return (
            f"Destination already exists: {destination}"
        )

    source.rename(
        destination
    )

    return (
        f"Renamed {source.name} "
        f"to {destination.name}"
    )


def delete_path(path):

    from core.safety import is_path_safe_for_deletion

    target = safe_path(path)

    safe, reason = is_path_safe_for_deletion(target)
    if not safe:
        return f"Safety refusal: {reason}"

    if not target.exists():

        return (
            f"Path does not exist: {target}"
        )

    if target.is_dir():

        shutil.rmtree(
            target
        )

    else:

        target.unlink()

    return (
        f"Deleted {target}"
    )

