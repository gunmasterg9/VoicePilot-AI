import sys

from PySide6.QtCore import Qt

from PySide6.QtWidgets import (
    QApplication
)

from ui.window import (
    OrionWindow,
    NeoWindow
)


def run_ui():

    app = QApplication(
        sys.argv
    )

    app.setApplicationName(
        "NEO AI"
    )

    app.setOrganizationName(
        "NEO AI"
    )


    app.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    window = NeoWindow()

    window.show()

    window.startup_animation()

    return app.exec()


run_neo_ui = run_ui
