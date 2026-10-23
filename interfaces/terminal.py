
from core.agent import OrionAgent


def run_terminal():

    agent = OrionAgent()

    print()
    print("=" * 60)
    print(
        "                      NEO AI"
    )
    print(
        "            Your Local AI PC Assistant"
    )
    print("=" * 60)
    print()

    print(
        "NEO is online."
    )

    print(
        "Type 'exit' to shut down NEO."
    )

    print()

    while True:

        try:

            user_input = input(
                "You > "
            ).strip()

        except KeyboardInterrupt:

            print(
                "\nNEO > Going offline."
            )

            break

        except EOFError:

            print(
                "\nNEO > Going offline."
            )

            break

        if not user_input:
            continue

        if user_input.lower() in {
            "exit",
            "quit",
            "neo exit",
            "neo quit",
            "orion exit",
            "orion quit",
            "go offline",
            "neo go offline",
            "orion go offline"
        }:

            print(
                "NEO > Going offline."
            )

            break

        response = agent.run(
            user_input
        )

        print()
        print(
            f"NEO > {response}"
        )
        print()


run_neo_terminal = run_terminal


