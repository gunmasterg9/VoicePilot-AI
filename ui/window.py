from PySide6.QtCore import (
    QObject,
    QThread,
    Signal,
    Slot,
    QTimer,
    QRectF,
    Qt
)

from PySide6.QtGui import (
    QPainter,
    QPen,
    QBrush,
    QColor,
    QFont
)

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QTextBrowser,
    QFrame,
    QMessageBox
)

from core.agent import OrionAgent, NeoAgent
from config import WINDOW_TITLE, APP_NAME, TAGLINE
from interfaces.tts import tts_manager
from ui.settings_dialog import SettingsDialog



# ================================================================
# ORION CORE
# ================================================================

class CoreOrb(QWidget):

    def __init__(self):

        super().__init__()

        self.setMinimumSize(
            400,
            400
        )

        self.phase = 0
        self.pulse = 0.0
        self.pulse_dir = 1

        self.state = "READY"

        self.timer = QTimer(
            self
        )

        self.timer.timeout.connect(
            self.animate
        )

        self.timer.start(
            30
        )

    def set_state(self, state):

        self.state = str(
            state
        ).upper()

        self.update()

    def animate(self):

        # State-driven animation dynamics
        speed = 2
        if self.state == "THINKING":
            speed = 5
        elif self.state == "SPEAKING":
            speed = 3
        elif self.state == "LISTENING":
            speed = 1.5
        elif self.state == "ERROR":
            speed = 4

        self.phase = (
            self.phase + speed
        ) % 360

        # Breathing pulse
        pulse_speed = 0.05 if self.state in {"LISTENING", "SPEAKING", "ERROR"} else 0.025
        self.pulse += pulse_speed * self.pulse_dir
        if self.pulse >= 1.0:
            self.pulse = 1.0
            self.pulse_dir = -1
        elif self.pulse <= 0.0:
            self.pulse = 0.0
            self.pulse_dir = 1

        self.update()

    def paintEvent(self, event):

        painter = QPainter(
            self
        )

        painter.setRenderHint(
            QPainter.Antialiasing
        )

        rect = QRectF(
            self.rect()
        )

        cx = rect.center().x()
        cy = rect.center().y()

        base = (
            min(
                rect.width(),
                rect.height()
            ) * 0.24
        )

        # Dynamic palettes based on operational state
        if self.state == "LISTENING":
            primary_color = QColor("#00f5a0")       # Neon Emerald
            secondary_color = QColor("#00d2ff")     # Electric Cyan
            center_bg = QColor("#021a12")
            text_color = QColor("#a7f3d0")
            status_text_color = QColor("#00f5a0")
        elif self.state == "THINKING":
            primary_color = QColor("#b388ff")       # Deep Violet
            secondary_color = QColor("#fbbf24")     # Amber Gold
            center_bg = QColor("#180a2b")
            text_color = QColor("#e9d5ff")
            status_text_color = QColor("#fbbf24")
        elif self.state == "SPEAKING":
            primary_color = QColor("#38bdf8")       # Vibrant Acoustic Cyan
            secondary_color = QColor("#818cf8")     # Indigo Pulse
            center_bg = QColor("#061c2a")
            text_color = QColor("#bae6fd")
            status_text_color = QColor("#38bdf8")
        elif self.state == "ERROR":
            primary_color = QColor("#ef4444")       # Alert Crimson
            secondary_color = QColor("#f59e0b")     # Warning Amber
            center_bg = QColor("#2b0606")
            text_color = QColor("#fca5a5")
            status_text_color = QColor("#ef4444")
        else:
            # READY / IDLE
            primary_color = QColor("#18dfff")       # Signature Orion Cyan
            secondary_color = QColor("#64f1ff")
            center_bg = QColor("#071722")
            text_color = QColor("#b8faff")
            status_text_color = QColor("#50cddd")

        # Outer backdrop ring
        painter.setPen(
            Qt.NoPen
        )

        painter.setBrush(
            QBrush(
                QColor("#050b12")
            )
        )

        painter.drawEllipse(
            QRectF(
                cx - base,
                cy - base,
                base * 2,
                base * 2
            )
        )

        pulse_offset = self.pulse * (8 if self.state in {"LISTENING", "SPEAKING", "ERROR"} else 3)

        # Rotating energy arcs
        for index in range(5):

            radius = (
                base
                + 30
                + index * 25
                + pulse_offset
            )

            pen = QPen(
                primary_color if index % 2 == 0 else secondary_color
            )

            pen.setWidth(
                1 if index > 1 else 2
            )

            painter.setPen(
                pen
            )

            start = (
                self.phase
                + index * 60
            )

            span = (
                100
                - index * 10
            )

            painter.drawArc(
                QRectF(
                    cx - radius,
                    cy - radius,
                    radius * 2,
                    radius * 2
                ),
                int(start * 16),
                int(span * 16)
            )

            painter.drawArc(
                QRectF(
                    cx - radius,
                    cy - radius,
                    radius * 2,
                    radius * 2
                ),
                int((start + 180) * 16),
                int(span * 16)
            )

        # Central Orb Ring
        painter.setPen(
            QPen(
                secondary_color,
                3
            )
        )

        painter.setBrush(
            QBrush(
                center_bg
            )
        )

        painter.drawEllipse(
            QRectF(
                cx - base,
                cy - base,
                base * 2,
                base * 2
            )
        )

        # Concentric inner wavelets
        for i in range(4):

            radius = (
                base
                * (
                    0.65
                    - i * 0.11
                )
            )

            painter.setPen(
                QPen(
                    primary_color,
                    1
                )
            )

            painter.drawEllipse(
                QRectF(
                    cx - radius,
                    cy - radius,
                    radius * 2,
                    radius * 2
                )
            )

        # Central Name
        painter.setPen(
            QPen(
                text_color
            )
        )

        painter.setFont(
            QFont(
                "Segoe UI",
                22,
                QFont.Bold
            )
        )

        painter.drawText(
            QRectF(
                cx - base,
                cy - 22,
                base * 2,
                32
            ),
            Qt.AlignCenter,
            "NEO"
        )


        # Sub-status indicator
        painter.setFont(
            QFont(
                "Consolas",
                9,
                QFont.Bold
            )
        )

        painter.setPen(
            QPen(
                status_text_color
            )
        )

        painter.drawText(
            QRectF(
                cx - base,
                cy + 15,
                base * 2,
                25
            ),
            Qt.AlignCenter,
            self.state
        )



# ================================================================
# AGENT WORKER
# ================================================================

class AgentWorker(QObject):

    finished = Signal(str)
    state = Signal(str)

    def __init__(
        self,
        agent,
        command
    ):

        super().__init__()

        self.agent = agent
        self.command = command

    @Slot()
    def run(self):

        try:

            self.state.emit(
                "THINKING"
            )

            response = (
                self.agent.run(
                    self.command
                )
            )

            self.finished.emit(
                str(
                    response
                    or "Command completed."
                )
            )

        except Exception as exc:

            self.finished.emit(
                f"NEO error: {exc}"
            )

# ================================================================
# VOICE WORKER
# ================================================================

class VoiceWorker(QObject):

    finished = Signal(str)
    state = Signal(str)
    log = Signal(str)

    def __init__(
        self,
        agent
    ):

        super().__init__()

        self.agent = agent

    @Slot()
    def run(self):

        try:

            try:
                import pythoncom
                pythoncom.CoInitialize()
            except Exception:
                pass

            from interfaces.voice import (
                VoiceInterface
            )

            voice = VoiceInterface(
                self.agent,
                output_callback=self.log.emit,
                state_callback=self.state.emit
            )

            response = (
                voice.process_voice_command()
            )

            self.finished.emit(
                str(
                    response
                    or ""
                )
            )

        except Exception as exc:

            self.state.emit("ERROR")
            self.log.emit(f"NEO > Voice error: {exc}")
            self.finished.emit(
                f"NEO voice error: {exc}"
            )


# ================================================================
# TTS TEST WORKER
# ================================================================

class TtsTestWorker(QObject):

    finished = Signal(str)
    state = Signal(str)
    log = Signal(str)

    def __init__(
        self,
        agent
    ):

        super().__init__()

        self.agent = agent

    @Slot()
    def run(self):

        try:

            try:
                import pythoncom
                pythoncom.CoInitialize()
            except Exception:
                pass

            from interfaces.voice import (
                VoiceInterface
            )

            voice = VoiceInterface(
                self.agent,
                output_callback=self.log.emit,
                state_callback=self.state.emit
            )

            test_text = "NEO audio playback operational. Natural neural voice synthesis ready."
            self.log.emit("NEO > [TTS TEST] Speaking test audio...")
            voice.speak(test_text)
            self.finished.emit("Audio playback test completed.")

        except Exception as exc:

            self.state.emit("ERROR")
            self.log.emit(f"NEO > [TTS ERROR]: {exc}")
            self.finished.emit(f"TTS error: {exc}")


# ================================================================
# MAIN WINDOW
# ================================================================

class OrionWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        self.setWindowTitle(
            WINDOW_TITLE
        )

        self.resize(
            1280,
            800
        )

        self.setMinimumSize(
            1000,
            650
        )

        self.agent = OrionAgent(
            confirm_callback=self.confirm_action
        )

        self.thread = None
        self.worker = None

        self.voice_thread = None
        self.voice_worker = None

        self.tts_thread = None
        self.tts_worker = None

        self.build_ui()
        self.apply_style()

    # ============================================================
    # UI
    # ============================================================

    def build_ui(self):

        root = QWidget()

        self.setCentralWidget(
            root
        )

        layout = QVBoxLayout(
            root
        )

        layout.setContentsMargins(
            25,
            20,
            25,
            20
        )

        layout.setSpacing(
            14
        )

        header = QHBoxLayout()

        title = QLabel(
            "NEO AI"
        )

        title.setObjectName(
            "title"
        )

        subtitle = QLabel(
            "YOUR LOCAL AI PC ASSISTANT"
        )

        subtitle.setObjectName(
            "subtitle"
        )

        self.status = QLabel(
            "● SYSTEM ONLINE"
        )

        self.status.setObjectName(
            "status"
        )

        header.addWidget(title)
        header.addWidget(subtitle)
        header.addStretch()
        header.addWidget(self.status)

        layout.addLayout(header)

        main = QHBoxLayout()

        main.setSpacing(
            20
        )

        self.orb = CoreOrb()

        main.addWidget(
            self.orb,
            3
        )

        side = QVBoxLayout()

        telemetry_panel = QFrame()

        telemetry_panel.setObjectName(
            "panel"
        )

        telemetry_layout = QVBoxLayout(
            telemetry_panel
        )

        telemetry_title = QLabel(
            "SYSTEM TELEMETRY"
        )

        telemetry_title.setObjectName(
            "panelTitle"
        )

        telemetry_layout.addWidget(
            telemetry_title
        )

        self.telemetry = QLabel(
            "AI CORE     ONLINE\n"
            "OLLAMA      LOCAL\n"
            "VOICE       READY\n"
            "MIC         ONLINE\n"
            "MODE        IDLE"
        )

        self.telemetry.setObjectName(
            "telemetry"
        )

        telemetry_layout.addWidget(
            self.telemetry
        )

        side.addWidget(
            telemetry_panel
        )

        chat_panel = QFrame()

        chat_panel.setObjectName(
            "panel"
        )

        chat_layout = QVBoxLayout(
            chat_panel
        )

        chat_title = QLabel(
            "TRANSCRIPT & COMMAND LOG"
        )

        chat_title.setObjectName(
            "panelTitle"
        )

        chat_layout.addWidget(
            chat_title
        )

        # Full scrollable transcript display
        self.chat = QTextBrowser()
        self.chat.setObjectName(
            "chat"
        )
        self.chat.setOpenExternalLinks(
            True
        )

        chat_layout.addWidget(
            self.chat
        )

        side.addWidget(
            chat_panel,
            2
        )

        main.addLayout(
            side,
            2
        )

        layout.addLayout(
            main,
            1
        )

        bottom = QHBoxLayout()

        self.input = QLineEdit()

        self.input.setPlaceholderText(
            "Enter a voice or PC command for NEO..."
        )

        self.input.returnPressed.connect(
            self.send_text
        )

        self.send_button = QPushButton(
            "EXECUTE"
        )

        self.send_button.clicked.connect(
            self.send_text
        )

        self.voice_button = QPushButton(
            "◉  VOICE"
        )

        self.voice_button.setObjectName(
            "voiceButton"
        )

        self.voice_button.clicked.connect(
            self.start_voice
        )

        self.tts_button = QPushButton(
            "🔊  TEST TTS"
        )

        self.tts_button.setObjectName(
            "ttsButton"
        )

        self.tts_button.clicked.connect(
            self.start_tts_test
        )

        self.stop_button = QPushButton(
            "⏹  STOP"
        )

        self.stop_button.setObjectName(
            "stopButton"
        )

        self.stop_button.clicked.connect(
            self.stop_action
        )

        self.settings_button = QPushButton(
            "⚙  SETTINGS"
        )

        self.settings_button.setObjectName(
            "settingsButton"
        )

        self.settings_button.clicked.connect(
            self.open_settings
        )

        bottom.addWidget(
            self.input,
            1
        )

        bottom.addWidget(
            self.send_button
        )

        bottom.addWidget(
            self.voice_button
        )

        bottom.addWidget(
            self.tts_button
        )

        bottom.addWidget(
            self.stop_button
        )

        bottom.addWidget(
            self.settings_button
        )

        layout.addLayout(
            bottom
        )

    # ============================================================
    # STYLE
    # ============================================================

    def apply_style(self):

        self.setStyleSheet(
            """
            QMainWindow,
            QWidget {
                background: #02070c;
                color: #bff7ff;
                font-family: "Segoe UI";
            }

            #title {
                color: #55eaff;
                font-size: 34px;
                font-weight: 700;
            }

            #subtitle {
                color: #397985;
                font-size: 9px;
                margin-left: 12px;
            }

            #status {
                color: #54e7a6;
                font-size: 11px;
                font-weight: 700;
            }

            #panel {
                background: #061018;
                border: 1px solid #123e4a;
                border-radius: 14px;
            }

            #panelTitle {
                color: #4de0f4;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1px;
            }

            #telemetry {
                color: #62c6d5;
                font-family: Consolas;
                font-size: 12px;
            }

            #chat {
                background: #02070b;
                border: 1px solid #0d3540;
                border-radius: 9px;
                padding: 10px;
                color: #9de8f3;
                font-family: Consolas, monospace;
                font-size: 11px;
            }

            QScrollBar:vertical {
                background: #02070b;
                width: 8px;
                border: none;
                margin: 0;
            }

            QScrollBar::handle:vertical {
                background: #113f4d;
                border-radius: 4px;
                min-height: 20px;
            }

            QScrollBar::handle:vertical:hover {
                background: #18dfff;
            }

            QLineEdit {
                background: #061018;
                border: 1px solid #155364;
                border-radius: 10px;
                padding: 13px;
                color: #d8fbff;
                font-size: 13px;
            }

            QLineEdit:focus {
                border: 1px solid #43e8ff;
            }

            QPushButton {
                background: #071923;
                border: 1px solid #1a7183;
                border-radius: 10px;
                padding: 12px 20px;
                color: #73e9f8;
                font-weight: 700;
            }

            QPushButton:hover {
                background: #0b2934;
                border: 1px solid #46eaff;
                color: #e0f9ff;
            }

            QPushButton:disabled {
                color: #35535b;
                border-color: #19333b;
            }

            #ttsButton {
                background: #071d28;
                border: 1px solid #1c6273;
                color: #38bdf8;
            }

            #ttsButton:hover {
                background: #0b2e3f;
                border: 1px solid #38bdf8;
                color: #bae6fd;
            }

            #stopButton {
                background: #1c0909;
                border: 1px solid #7f1d1d;
                color: #f87171;
            }

            #stopButton:hover {
                background: #2e0d0d;
                border: 1px solid #ef4444;
                color: #fca5a5;
            }

            #settingsButton {
                background: #0d1926;
                border: 1px solid #1e3a5f;
                color: #93c5fd;
            }

            #settingsButton:hover {
                background: #13273e;
                border: 1px solid #3b82f6;
                color: #dbeafe;
            }
            """
        )

    # ============================================================
    # LOG / TRANSCRIPT
    # ============================================================

    def append_chat(
        self,
        message
    ):

        msg_str = str(message).strip()

        if msg_str.startswith("YOU >"):
            content = msg_str[5:].strip()
            html = f"<div style='margin-bottom:6px;'><span style='color: #38bdf8; font-weight: bold;'>YOU &gt;</span> <span style='color: #f1f5f9;'>{content}</span></div>"
        elif msg_str.startswith("NEO >"):
            content = msg_str[5:].strip()
            html = f"<div style='margin-bottom:6px;'><span style='color: #00f5a0; font-weight: bold;'>NEO &gt;</span> <span style='color: #bbf7d0;'>{content}</span></div>"
        elif msg_str.startswith("ORION >"):
            content = msg_str[7:].strip()
            html = f"<div style='margin-bottom:6px;'><span style='color: #00f5a0; font-weight: bold;'>NEO &gt;</span> <span style='color: #bbf7d0;'>{content}</span></div>"
        elif "error" in msg_str.lower() or "[fail]" in msg_str.lower():
            html = f"<div style='margin-bottom:6px;'><span style='color: #ef4444; font-weight: bold;'>[ERROR]</span> <span style='color: #fca5a5;'>{msg_str}</span></div>"
        elif "●" in msg_str or "[ok]" in msg_str.lower() or "online" in msg_str.lower():
            html = f"<div style='margin-bottom:6px;'><span style='color: #22d3ee; font-weight: bold;'>●</span> <span style='color: #a5f3fc;'>{msg_str}</span></div>"
        else:
            html = f"<div style='margin-bottom:6px;'><span style='color: #7dd3fc;'>{msg_str}</span></div>"

        self.chat.append(html)

        scrollbar = self.chat.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    # ============================================================
    # STATE
    # ============================================================

    def set_state(
        self,
        state
    ):

        state = str(
            state
        ).upper()

        self.orb.set_state(
            state
        )

        status_colors = {
            "READY": "#54e7a6",
            "LISTENING": "#00f5a0",
            "THINKING": "#fbbf24",
            "SPEAKING": "#38bdf8",
            "ERROR": "#ef4444"
        }

        color = status_colors.get(state, "#54e7a6")
        self.status.setStyleSheet(f"color: {color};")
        self.status.setText("● " + state)

        voice_state = (
            "ACTIVE"
            if state in {
                "LISTENING",
                "SPEAKING"
            }
            else "READY"
        )

        try:
            from core.llm import llm_manager
            model_name = llm_manager.get_active_model()
        except Exception:
            model_name = "OLLAMA"

        try:
            tts_status = tts_manager.get_status()
            provider_name = tts_status.get("provider", "NEURAL").upper()
        except Exception:
            provider_name = "NEURAL"

        self.telemetry.setText(
            f"AI CORE     ONLINE\n"
            f"MODEL       {model_name[:12]}\n"
            f"TTS         {provider_name[:12]}\n"
            f"VOICE       {voice_state}\n"
            f"MODE        {state}"
        )

        if state == "LISTENING":
            self.voice_button.setText("■  LISTENING...")
            self.voice_button.setStyleSheet(
                "background: #064e3b; border: 1px solid #00f5a0; color: #a7f3d0;"
            )
        elif state == "SPEAKING":
            self.tts_button.setStyleSheet(
                "background: #0c3347; border: 1px solid #38bdf8; color: #bae6fd;"
            )
        else:
            self.voice_button.setText("◉  VOICE")
            self.voice_button.setStyleSheet("")
            self.tts_button.setStyleSheet("")

    # ============================================================
    # CONFIRM
    # ============================================================

    def confirm_action(
        self,
        message
    ):

        result = QMessageBox.question(
            self,
            "NEO AI Confirmation",
            str(message),
            QMessageBox.Yes
            | QMessageBox.No,
            QMessageBox.No
        )

        return (
            result
            == QMessageBox.Yes
        )

    # ============================================================
    # TEXT
    # ============================================================

    def send_text(self):

        command = (
            self.input.text().strip()
        )

        if not command:
            return

        if (
            self.thread
            and self.thread.isRunning()
        ):
            return

        if (
            self.voice_thread
            and self.voice_thread.isRunning()
        ):
            return

        if (
            self.tts_thread
            and self.tts_thread.isRunning()
        ):
            return

        self.input.clear()

        self.append_chat(
            "YOU > " + command
        )

        self.set_state(
            "THINKING"
        )

        self.set_inputs_enabled(
            False
        )

        self.thread = QThread()

        self.worker = AgentWorker(
            self.agent,
            command
        )

        self.worker.moveToThread(
            self.thread
        )

        self.thread.started.connect(
            self.worker.run
        )

        self.worker.state.connect(
            self.set_state
        )

        self.worker.finished.connect(
            self.text_finished
        )

        self.worker.finished.connect(
            self.thread.quit
        )

        self.worker.finished.connect(
            self.worker.deleteLater
        )

        self.thread.finished.connect(
            self.thread.deleteLater
        )

        self.thread.finished.connect(
            self.text_thread_done
        )

        self.thread.start()

    @Slot(str)
    def text_finished(
        self,
        response
    ):

        self.append_chat(
            "NEO > " + response
        )

        self.set_state(
            "READY"
        )

    def text_thread_done(self):

        self.thread = None
        self.worker = None

        self.set_inputs_enabled(
            True
        )

    # ============================================================
    # VOICE
    # ============================================================

    def start_voice(self):

        if (
            self.voice_thread
            and self.voice_thread.isRunning()
        ):
            return

        if (
            self.thread
            and self.thread.isRunning()
        ):
            return

        if (
            self.tts_thread
            and self.tts_thread.isRunning()
        ):
            return

        self.set_inputs_enabled(
            False
        )

        self.set_state(
            "LISTENING"
        )

        self.voice_thread = QThread()

        self.voice_worker = VoiceWorker(
            self.agent
        )

        self.voice_worker.moveToThread(
            self.voice_thread
        )

        self.voice_thread.started.connect(
            self.voice_worker.run
        )

        self.voice_worker.state.connect(
            self.set_state
        )

        self.voice_worker.log.connect(
            self.append_chat
        )

        self.voice_worker.finished.connect(
            self.voice_finished
        )

        self.voice_worker.finished.connect(
            self.voice_thread.quit
        )

        self.voice_worker.finished.connect(
            self.voice_worker.deleteLater
        )

        self.voice_thread.finished.connect(
            self.voice_thread.deleteLater
        )

        self.voice_thread.finished.connect(
            self.voice_thread_done
        )

        self.voice_thread.start()

    @Slot(str)
    def voice_finished(
        self,
        response
    ):

        self.set_state(
            "READY"
        )

    def voice_thread_done(self):

        self.voice_thread = None
        self.voice_worker = None

        self.set_inputs_enabled(
            True
        )

        self.set_state(
            "READY"
        )

    # ============================================================
    # TTS TEST
    # ============================================================

    def start_tts_test(self):

        if (
            self.tts_thread
            and self.tts_thread.isRunning()
        ):
            return

        if (
            self.voice_thread
            and self.voice_thread.isRunning()
        ):
            return

        if (
            self.thread
            and self.thread.isRunning()
        ):
            return

        self.set_inputs_enabled(
            False
        )

        self.set_state(
            "SPEAKING"
        )

        self.tts_thread = QThread()

        self.tts_worker = TtsTestWorker(
            self.agent
        )

        self.tts_worker.moveToThread(
            self.tts_thread
        )

        self.tts_thread.started.connect(
            self.tts_worker.run
        )

        self.tts_worker.state.connect(
            self.set_state
        )

        self.tts_worker.log.connect(
            self.append_chat
        )

        self.tts_worker.finished.connect(
            self.tts_test_finished
        )

        self.tts_worker.finished.connect(
            self.tts_thread.quit
        )

        self.tts_worker.finished.connect(
            self.tts_worker.deleteLater
        )

        self.tts_thread.finished.connect(
            self.tts_thread.deleteLater
        )

        self.tts_thread.finished.connect(
            self.tts_test_done
        )

        self.tts_thread.start()

    @Slot(str)
    def tts_test_finished(
        self,
        result
    ):

        self.append_chat(
            f"NEO > [TTS OK]: {result}"
        )

        self.set_state(
            "READY"
        )

    def tts_test_done(self):

        self.tts_thread = None
        self.tts_worker = None

        self.set_inputs_enabled(
            True
        )

        self.set_state(
            "READY"
        )

    # ============================================================
    # STOP / CANCEL ACTION
    # ============================================================

    def stop_action(self):

        tts_manager.stop()
        self.append_chat("NEO > [STOPPED] Speech synthesis halted and current operations cancelled.")
        self.set_state("READY")
        self.set_inputs_enabled(True)

    # ============================================================
    # SETTINGS MODAL
    # ============================================================

    def open_settings(self):

        dialog = SettingsDialog(self)
        if dialog.exec():
            self.append_chat("NEO > Settings and configurations updated successfully.")
            self.set_state("READY")

    def set_inputs_enabled(
        self,
        enabled
    ):

        self.input.setEnabled(enabled)
        self.send_button.setEnabled(enabled)
        self.voice_button.setEnabled(enabled)
        self.tts_button.setEnabled(enabled)
        if hasattr(self, "settings_button"):
            self.settings_button.setEnabled(enabled)
        if hasattr(self, "stop_button"):
            # Stop button stays available to cancel ongoing tasks
            self.stop_button.setEnabled(True)

    # ============================================================
    # STARTUP
    # ============================================================

    def startup_animation(self):

        self.append_chat(
            "NEO > All core systems online. Your Local AI PC Assistant is ready."
        )

        self.set_state(
            "READY"
        )


NeoWindow = OrionWindow

__all__ = [
    "NeoWindow",
    "OrionWindow",
    "CoreOrb",
    "AgentWorker",
    "VoiceWorker",
    "TtsTestWorker"
]

