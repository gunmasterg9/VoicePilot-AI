import argparse
import sys
import time

from config import (
    OLLAMA_MODEL
)


def boot_sequence():

    print()

    print(
        "=" * 64
    )

    print(
        "                         NEO AI"
    )

    print(
        "               Your Local AI PC Assistant"
    )

    print(
        "=" * 64
    )

    print()

    steps = [
        "Initializing NEO AI core",
        "Loading configuration",
        "Checking local AI engine",
        f"Preparing model: {OLLAMA_MODEL}",
        "Loading tool registry",
        "Loading system interfaces",
        "Preparing graphical interface"
    ]

    for step in steps:

        print(
            f"[BOOT] {step}..."
        )

        time.sleep(
            0.08
        )

    try:

        from core.llm import (
            check_ollama
        )

        if check_ollama():

            print(
                "[ OK ] Ollama connection established"
            )

        else:

            print(
                "[WARN] Ollama is not reachable"
            )

            print(
                "[WARN] Direct commands will still work."
            )

    except Exception as exc:

        print(
            f"[WARN] Ollama check failed: {exc}"
        )

    print()

    print(
        "=" * 64
    )

    print(
        "                    NEO SYSTEMS ONLINE"
    )

    print(
        "=" * 64
    )

    print()



def main():

    parser = argparse.ArgumentParser(
        description="NEO AI — Your Local AI PC Assistant"
    )

    parser.add_argument(
        "--terminal",
        action="store_true"
    )

    parser.add_argument(
        "--voice",
        action="store_true"
    )

    parser.add_argument(
        "--server",
        action="store_true"
    )

    args = parser.parse_args()

    boot_sequence()

    if args.terminal:

        from interfaces.terminal import (
            run_terminal
        )

        run_terminal()

        return

    if args.voice:

        from core.agent import (
            OrionAgent
        )

        from interfaces.voice import (
            VoiceInterface
        )

        agent = OrionAgent()

        voice = VoiceInterface(
            agent
        )

        voice.speak(
            "NEO is online."
        )


        while True:

            try:

                command = input(
                    "Press ENTER to speak or type exit: "
                ).strip()

                if command.lower() == "exit":

                    break

                voice.process_voice_command()

            except KeyboardInterrupt:

                break

        return

    if args.server:

        from interfaces.api import (
            run_server
        )

        run_server()

        return

    from ui.app import (
        run_ui
    )

    sys.exit(
        run_ui()
    )


if __name__ == "__main__":

    main()
