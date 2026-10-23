
import os
import subprocess
import shutil
from pathlib import Path


def normalize(text):

    return (
        str(text)
        .lower()
        .replace(".exe", "")
        .replace(".lnk", "")
        .strip()
    )


def _search_start_menu(target):

    target = normalize(target)

    locations = [
        Path(
            os.environ.get("APPDATA", "")
        ) / "Microsoft/Windows/Start Menu/Programs",

        Path(
            os.environ.get("PROGRAMDATA", "")
        ) / "Microsoft/Windows/Start Menu/Programs"
    ]

    candidates = []

    for location in locations:

        if not location.exists():
            continue

        try:
            candidates.extend(
                location.rglob("*")
            )
        except Exception:
            continue

    best = None
    best_score = 0

    for item in candidates:

        if item.suffix.lower() not in {
            ".lnk",
            ".exe",
            ".appref-ms"
        }:
            continue

        name = normalize(item.stem)

        if name == target:
            return item

        score = 0

        if target in name:
            score += 4

        target_words = set(
            target.split()
        )

        name_words = set(
            name.split()
        )

        score += len(
            target_words & name_words
        )

        if score > best_score:

            best_score = score
            best = item

    return best


def _search_path(target):

    target = normalize(target)

    executable = shutil.which(target)

    if executable:
        return Path(executable)

    executable = shutil.which(
        target + ".exe"
    )

    if executable:
        return Path(executable)

    return None


def _search_common_locations(target):

    target = normalize(target)

    roots = [
        Path(
            os.environ.get(
                "PROGRAMFILES",
                ""
            )
        ),

        Path(
            os.environ.get(
                "PROGRAMFILES(X86)",
                ""
            )
        ),

        Path(
            os.environ.get(
                "LOCALAPPDATA",
                ""
            )
        )
    ]

    for root in roots:

        if not root.exists():
            continue

        try:

            for item in root.rglob("*"):

                if item.suffix.lower() != ".exe":
                    continue

                if normalize(item.stem) == target:
                    return item

        except (
            PermissionError,
            OSError
        ):
            continue

    return None


def find_application(target):

    result = _search_path(target)

    if result:
        return result

    result = _search_start_menu(target)

    if result:
        return result

    return _search_common_locations(
        target
    )


def launch_application(path):

    path = Path(path)

    if not path.exists():

        return (
            False,
            "Application no longer exists."
        )

    try:

        os.startfile(
            str(path)
        )

        return (
            True,
            f"Opened {path.stem}."
        )

    except Exception:

        try:

            subprocess.Popen(
                [str(path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            return (
                True,
                f"Opened {path.stem}."
            )

        except Exception as exc:

            return (
                False,
                f"Could not open application: {exc}"
            )


def find_and_launch_application(target):

    application = find_application(
        target
    )

    if not application:
        return False, None

    return launch_application(
        application
    )
