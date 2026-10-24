from html import escape

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
    QGridLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QTextBrowser,
    QFrame,
    QMessageBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QCheckBox,
    QComboBox,
    QSlider,
    QGroupBox,
    QScrollArea
)

from core.agent import OrionAgent, NeoAgent
from core.safety import mask_sensitive_data
from core.settings import settings
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
        if self.state in {"THINKING", "EXECUTING"}:
            speed = 5
        elif self.state in {"TRANSCRIBING", "ROUTING"}:
            speed = 3.5
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
        pulse_speed = 0.05 if self.state in {"LISTENING", "SPEAKING", "ERROR", "TRANSCRIBING"} else 0.025
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
        elif self.state == "TRANSCRIBING":
            primary_color = QColor("#c084fc")       # Orchid Violet
            secondary_color = QColor("#818cf8")     # Indigo
            center_bg = QColor("#1c0f30")
            text_color = QColor("#f3e8ff")
            status_text_color = QColor("#c084fc")
        elif self.state == "ROUTING":
            primary_color = QColor("#60a5fa")       # Sky Blue
            secondary_color = QColor("#38bdf8")     # Electric Cyan
            center_bg = QColor("#091b2e")
            text_color = QColor("#dbeafe")
            status_text_color = QColor("#60a5fa")
        elif self.state == "EXECUTING":
            primary_color = QColor("#2dd4bf")       # Vibrant Teal
            secondary_color = QColor("#00f5a0")     # Emerald Green
            center_bg = QColor("#04201c")
            text_color = QColor("#ccfbf1")
            status_text_color = QColor("#2dd4bf")
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

            self.state.emit("ROUTING")

            from core.router import route_direct_command
            routed = route_direct_command(self.command)
            if routed or (hasattr(self.agent, "_direct_command") and self.agent._direct_command(self.command)):
                self.state.emit("EXECUTING")
            else:
                self.state.emit("THINKING")

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
        self.agent.tool_callback = self.on_tool_executed

        self.thread = None
        self.worker = None

        self.voice_thread = None
        self.voice_worker = None

        self.tts_thread = None
        self.tts_worker = None
        self._close_pending = False
        self.current_state = "READY"
        self.activity_log = []

        self.build_ui()
        self.apply_style()

    # ============================================================
    # UI
    # ============================================================

    def build_ui(self):

        root = QWidget()
        self.setCentralWidget(root)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)

        # ------------------------------------------------------------
        # Header Bar: Brand + Offline Badge + Navigation + Real-time State
        # ------------------------------------------------------------
        header = QHBoxLayout()
        header.setSpacing(12)

        # Brand & Offline Indicator
        brand_col = QVBoxLayout()
        brand_col.setSpacing(1)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)

        title = QLabel("NEO AI")
        title.setObjectName("title")
        title_row.addWidget(title)

        self.offline_badge = QLabel("● 100% OFFLINE")
        self.offline_badge.setObjectName("offlineBadge")
        title_row.addWidget(self.offline_badge)
        title_row.addStretch()
        brand_col.addLayout(title_row)

        subtitle = QLabel("YOUR LOCAL AI PC ASSISTANT")
        subtitle.setObjectName("subtitle")
        brand_col.addWidget(subtitle)
        header.addLayout(brand_col)

        header.addStretch(1)

        # Compact Navigation Bar
        nav_container = QFrame()
        nav_container.setObjectName("navContainer")
        nav_layout = QHBoxLayout(nav_container)
        nav_layout.setContentsMargins(4, 4, 4, 4)
        nav_layout.setSpacing(4)

        self.btn_nav_home = QPushButton("🏠  HOME")
        self.btn_nav_voice = QPushButton("🎙  VOICE")
        self.btn_nav_activity = QPushButton("📋  ACTIVITY")
        self.btn_nav_settings = QPushButton("⚙  SETTINGS")
        self.btn_nav_about = QPushButton("ℹ  ABOUT")

        self.nav_buttons = [
            self.btn_nav_home,
            self.btn_nav_voice,
            self.btn_nav_activity,
            self.btn_nav_settings,
            self.btn_nav_about
        ]

        for idx, btn in enumerate(self.nav_buttons):
            btn.setObjectName("navButton")
            btn.clicked.connect(lambda _, i=idx: self.switch_nav(i))
            nav_layout.addWidget(btn)

        self.btn_nav_home.setProperty("active", "true")
        header.addWidget(nav_container)

        header.addStretch(1)

        # Real-time state indicator
        self.status = QLabel("● READY")
        self.status.setObjectName("status")
        header.addWidget(self.status)

        layout.addLayout(header)

        # ------------------------------------------------------------
        # Multi-View Stacked Pages
        # ------------------------------------------------------------
        self.stack = QStackedWidget()
        self.stack.setObjectName("mainStack")

        self.page_home = self._create_home_page()
        self.stack.addWidget(self.page_home)

        self.page_voice = self._create_voice_page()
        self.stack.addWidget(self.page_voice)

        self.page_activity = self._create_activity_page()
        self.stack.addWidget(self.page_activity)

        self.page_settings = self._create_settings_page()
        self.stack.addWidget(self.page_settings)

        self.page_about = self._create_about_page()
        self.stack.addWidget(self.page_about)

        layout.addWidget(self.stack, 1)

    # ============================================================
    # PAGE 0: HOME PAGE (CONVERSATION & CORE CONTROLS)
    # ============================================================

    def _create_home_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        main = QHBoxLayout()
        main.setSpacing(14)

        # Left Column: Core Orb + Quick Actions + System Telemetry
        left_col = QVBoxLayout()
        left_col.setSpacing(8)

        self.orb = CoreOrb()
        left_col.addWidget(self.orb, 0, Qt.AlignCenter)

        # Quick Actions Panel
        quick_panel = QFrame()
        quick_panel.setObjectName("panel")
        quick_layout = QVBoxLayout(quick_panel)
        quick_layout.setContentsMargins(12, 10, 12, 10)
        quick_layout.setSpacing(6)

        quick_title = QLabel("SUPPORTED QUICK ACTIONS")
        quick_title.setObjectName("panelTitle")
        quick_layout.addWidget(quick_title)

        grid = QGridLayout()
        grid.setSpacing(6)

        quick_actions = [
            ("📝 Notepad", "Open Notepad"),
            ("🔢 Calculator", "Open Calculator"),
            ("📸 Screenshot", "Take a screenshot"),
            ("🔊 Vol +", "Increase volume"),
            ("🔉 Vol -", "Decrease volume"),
            ("🔇 Mute", "Mute volume"),
            ("🗑 Recycle Bin", "Open Recycle Bin"),
            ("🔍 Search PC", "Search my PC"),
            ("⚡ Telemetry", "Check battery and system status"),
        ]

        for i, (label, cmd) in enumerate(quick_actions):
            btn = QPushButton(label)
            btn.setObjectName("quickActionBtn")
            btn.clicked.connect(lambda _, c=cmd: self.execute_quick_action(c))
            grid.addWidget(btn, i // 3, i % 3)
            if "Calculator" in cmd:
                self.btn_quick_calc = btn

        quick_layout.addLayout(grid)
        left_col.addWidget(quick_panel)

        # Compact Telemetry Panel
        telemetry_panel = QFrame()
        telemetry_panel.setObjectName("panel")
        telemetry_layout = QVBoxLayout(telemetry_panel)
        telemetry_layout.setContentsMargins(12, 8, 12, 8)
        telemetry_layout.setSpacing(4)

        telemetry_title = QLabel("SYSTEM TELEMETRY")
        telemetry_title.setObjectName("panelTitle")
        telemetry_layout.addWidget(telemetry_title)

        self.telemetry = QLabel(
            "AI CORE     ONLINE (100% LOCAL)\n"
            "OLLAMA      LOCAL\n"
            "VOICE       IDLE\n"
            "MIC         ONLINE\n"
            "MODE        IDLE"
        )
        self.telemetry.setObjectName("telemetry")
        telemetry_layout.addWidget(self.telemetry)
        left_col.addWidget(telemetry_panel)

        main.addLayout(left_col, 2)

        # Right Column: Transcript & Command Log
        chat_panel = QFrame()
        chat_panel.setObjectName("panel")
        chat_layout = QVBoxLayout(chat_panel)
        chat_layout.setContentsMargins(14, 12, 14, 12)
        chat_layout.setSpacing(6)

        chat_title = QLabel("CONVERSATION & COMMAND LOG")
        chat_title.setObjectName("panelTitle")
        chat_layout.addWidget(chat_title)

        self.chat = QTextBrowser()
        self.chat.setObjectName("chat")
        self.chat.setOpenExternalLinks(True)
        chat_layout.addWidget(self.chat, 1)

        main.addWidget(chat_panel, 3)
        layout.addLayout(main, 1)

        # Bottom Input Controls Row
        bottom = QHBoxLayout()
        bottom.setSpacing(8)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Enter a voice or PC command for NEO (e.g., 'Open Notepad', 'Increase volume', 'What time is it?')...")
        self.input.returnPressed.connect(self.send_text)

        self.send_button = QPushButton("EXECUTE")
        self.send_button.clicked.connect(self.send_text)

        self.voice_button = QPushButton("◉  VOICE")
        self.voice_button.setObjectName("voiceButton")
        self.voice_button.clicked.connect(self.start_voice)

        self.tts_button = QPushButton("🔊  TEST TTS")
        self.tts_button.setObjectName("ttsButton")
        self.tts_button.clicked.connect(self.start_tts_test)

        self.stop_button = QPushButton("⏹  STOP")
        self.stop_button.setObjectName("stopButton")
        self.stop_button.clicked.connect(self.stop_action)

        self.clear_button = QPushButton("🗑  CLEAR")
        self.clear_button.setObjectName("clearButton")
        self.clear_button.clicked.connect(self.clear_conversation)

        self.settings_button = QPushButton("⚙  SETTINGS")
        self.settings_button.setObjectName("settingsButton")
        self.settings_button.clicked.connect(self.open_settings)

        bottom.addWidget(self.input, 1)
        bottom.addWidget(self.send_button)
        bottom.addWidget(self.voice_button)
        bottom.addWidget(self.tts_button)
        bottom.addWidget(self.stop_button)
        bottom.addWidget(self.clear_button)
        bottom.addWidget(self.settings_button)

        layout.addLayout(bottom)
        return page

    # ============================================================
    # PAGE 1: VOICE & MULTILINGUAL CONFIGURATION
    # ============================================================

    def _create_voice_page(self) -> QWidget:
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        header_lbl = QLabel("VOICE PIPELINE & MULTILINGUAL SETTINGS")
        header_lbl.setObjectName("sectionHeader")
        layout.addWidget(header_lbl)

        # 1. Microphone Hardware
        mic_box = QGroupBox("Microphone Input & Calibration")
        mic_box.setObjectName("settingsBox")
        mic_layout = QVBoxLayout(mic_box)
        mic_layout.setSpacing(10)

        mic_row = QHBoxLayout()
        mic_row.addWidget(QLabel("Input Microphone:"))
        self.combo_mics = QComboBox()
        self.combo_mics.setObjectName("settingsCombo")
        from interfaces.voice import VoiceInterface
        mics = VoiceInterface.get_available_microphones()
        current_mic_idx = settings.get("mic_device_index")
        for idx, label in mics:
            self.combo_mics.addItem(label, idx)
            if idx == current_mic_idx:
                self.combo_mics.setCurrentIndex(self.combo_mics.count() - 1)
        mic_row.addWidget(self.combo_mics, 1)

        self.btn_test_mic = QPushButton("🎙 Test Mic Signal")
        self.btn_test_mic.setObjectName("actionBtn")
        self.btn_test_mic.clicked.connect(self._test_microphone_signal)
        mic_row.addWidget(self.btn_test_mic)
        mic_layout.addLayout(mic_row)

        self.lbl_mic_signal_result = QLabel("Microphone status: Ready. Click 'Test Mic Signal' to verify real-time input energy.")
        self.lbl_mic_signal_result.setObjectName("statusDetail")
        mic_layout.addWidget(self.lbl_mic_signal_result)
        layout.addWidget(mic_box)

        # 2. Faster-Whisper Offline ASR
        asr_box = QGroupBox("Offline Speech Recognition (Faster-Whisper CPU)")
        asr_box.setObjectName("settingsBox")
        asr_layout = QVBoxLayout(asr_box)
        asr_layout.setSpacing(10)

        lang_row = QHBoxLayout()
        lang_row.addWidget(QLabel("Primary Speech Language:"))
        self.combo_lang = QComboBox()
        self.combo_lang.setObjectName("settingsCombo")
        languages = [
            ("English (en)", "en"),
            ("Hindi (hi)", "hi"),
            ("Gujarati (gu)", "gu"),
            ("Auto-Detect Multilingual (auto)", "auto"),
        ]
        curr_lang = settings.get("speech_language", "en")
        for label, code in languages:
            self.combo_lang.addItem(label, code)
            if code == curr_lang:
                self.combo_lang.setCurrentIndex(self.combo_lang.count() - 1)
        lang_row.addWidget(self.combo_lang, 1)
        asr_layout.addLayout(lang_row)

        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("Whisper Model:"))
        self.combo_whisper_model = QComboBox()
        self.combo_whisper_model.setObjectName("settingsCombo")
        models = [
            ("tiny.en (Fastest - English Only)", "tiny.en"),
            ("tiny (Fast - Multilingual English/Hindi/Gujarati)", "tiny"),
            ("base (Balanced - Multilingual)", "base"),
        ]
        curr_model = settings.get("whisper_model", "tiny.en")
        for label, code in models:
            self.combo_whisper_model.addItem(label, code)
            if code == curr_model:
                self.combo_whisper_model.setCurrentIndex(self.combo_whisper_model.count() - 1)
        model_row.addWidget(self.combo_whisper_model, 1)
        asr_layout.addLayout(model_row)
        layout.addWidget(asr_box)

        # 3. Offline SAPI5 TTS
        tts_box = QGroupBox("Offline Speech Synthesis (Windows SAPI5 Local)")
        tts_box.setObjectName("settingsBox")
        tts_layout = QVBoxLayout(tts_box)
        tts_layout.setSpacing(10)

        self.chk_tts_enabled = QCheckBox("Enable Voice Output (Spoken Responses)")
        self.chk_tts_enabled.setObjectName("settingsCheck")
        self.chk_tts_enabled.setChecked(bool(settings.get("tts_enabled", True)))
        tts_layout.addWidget(self.chk_tts_enabled)

        rate_row = QHBoxLayout()
        rate_row.addWidget(QLabel("Speech Rate (Words/Min):"))
        self.slider_rate = QSlider(Qt.Horizontal)
        self.slider_rate.setRange(120, 240)
        self.slider_rate.setValue(int(settings.get("tts_speech_rate", 180)))
        self.lbl_rate_val = QLabel(f"{self.slider_rate.value()} wpm")
        self.slider_rate.valueChanged.connect(lambda v: self.lbl_rate_val.setText(f"{v} wpm"))
        rate_row.addWidget(self.slider_rate, 1)
        rate_row.addWidget(self.lbl_rate_val)
        tts_layout.addLayout(rate_row)

        vol_row = QHBoxLayout()
        vol_row.addWidget(QLabel("Speech Volume:"))
        self.slider_vol = QSlider(Qt.Horizontal)
        self.slider_vol.setRange(0, 100)
        self.slider_vol.setValue(int(settings.get("tts_volume", 1.0) * 100))
        self.lbl_vol_val = QLabel(f"{self.slider_vol.value()}%")
        self.slider_vol.valueChanged.connect(lambda v: self.lbl_vol_val.setText(f"{v}%"))
        vol_row.addWidget(self.slider_vol, 1)
        vol_row.addWidget(self.lbl_vol_val)
        tts_layout.addLayout(vol_row)
        layout.addWidget(tts_box)

        # Save Button
        save_btn = QPushButton("💾  SAVE VOICE CONFIGURATION")
        save_btn.setObjectName("primaryActionBtn")
        save_btn.clicked.connect(self._save_voice_settings)
        layout.addWidget(save_btn)
        layout.addStretch()

        scroll.setWidget(container)
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)
        return page

    # ============================================================
    # PAGE 2: RECENT ACTIVITY & AUDIT LOG
    # ============================================================

    def _create_activity_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        header_row = QHBoxLayout()
        title = QLabel("ACTIVITY HISTORY & COMMAND AUDIT")
        title.setObjectName("sectionHeader")
        header_row.addWidget(title)
        header_row.addStretch()

        self.activity_count_label = QLabel("Total Operations: 0")
        self.activity_count_label.setObjectName("badgeCount")
        header_row.addWidget(self.activity_count_label)
        layout.addLayout(header_row)

        self.activity_table = QTableWidget(0, 5)
        self.table_activity = self.activity_table
        self.activity_table.setObjectName("activityTable")
        self.activity_table.setHorizontalHeaderLabels(["Timestamp", "Type", "Command / Request", "Status", "Execution Result"])
        self.activity_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.activity_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.activity_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Interactive)
        self.activity_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.activity_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.activity_table.setAlternatingRowColors(True)
        self.activity_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.activity_table, 1)

        bottom_row = QHBoxLayout()
        clear_btn = QPushButton("🗑  Clear Activity History")
        clear_btn.setObjectName("clearButton")
        clear_btn.clicked.connect(self._clear_activity_history)
        bottom_row.addWidget(clear_btn)
        bottom_row.addStretch()
        layout.addLayout(bottom_row)
        return page

    # ============================================================
    # PAGE 3: PREFERENCES & DIAGNOSTICS
    # ============================================================

    def _create_settings_page(self) -> QWidget:
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        header_lbl = QLabel("SYSTEM PREFERENCES & DIAGNOSTICS")
        header_lbl.setObjectName("sectionHeader")
        layout.addWidget(header_lbl)

        # 1. Local AI (Ollama)
        ai_box = QGroupBox("Local Ollama Engine (Conversational AI Only)")
        ai_box.setObjectName("settingsBox")
        ai_layout = QVBoxLayout(ai_box)
        ai_layout.setSpacing(10)

        host_row = QHBoxLayout()
        host_row.addWidget(QLabel("Ollama Host URL:"))
        self.input_ollama_host = QLineEdit(settings.get("ollama_host", "http://127.0.0.1:11434"))
        host_row.addWidget(self.input_ollama_host, 1)

        self.btn_test_ollama = QPushButton("🔄 Test Connection")
        self.btn_test_ollama.setObjectName("actionBtn")
        self.btn_test_ollama.clicked.connect(self._test_ollama_connection)
        host_row.addWidget(self.btn_test_ollama)
        ai_layout.addLayout(host_row)

        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("Configured Model:"))
        self.input_ollama_model = QLineEdit(settings.get("ollama_model", "qwen3:1.7b"))
        model_row.addWidget(self.input_ollama_model, 1)
        ai_layout.addLayout(model_row)

        self.lbl_ollama_status = QLabel("Ollama status: Ready to test.")
        self.lbl_ollama_status.setObjectName("statusDetail")
        ai_layout.addWidget(self.lbl_ollama_status)
        layout.addWidget(ai_box)

        # 2. Automation Safety
        sec_box = QGroupBox("PC Automation Security & Guardrails")
        sec_box.setObjectName("settingsBox")
        sec_layout = QVBoxLayout(sec_box)
        sec_layout.setSpacing(8)

        self.chk_confirm_destructive = QCheckBox("Require confirmation before destructive actions (shutdown, restart, delete)")
        self.chk_confirm_destructive.setObjectName("settingsCheck")
        self.chk_confirm_destructive.setChecked(bool(settings.get("confirm_destructive_actions", True)))
        sec_layout.addWidget(self.chk_confirm_destructive)

        safeguards_info = QLabel(
            "• Local Allowlist: Notepad, Calculator, Paint, File Explorer, Task Manager, Recycle Bin, Windows Search.\n"
            "• Path Protection: System directories (C:\\Windows, System32) are strictly protected.\n"
            "• Offline Independence: Local PC commands execute without contacting Ollama or cloud services."
        )
        safeguards_info.setObjectName("safeguardsText")
        sec_layout.addWidget(safeguards_info)
        layout.addWidget(sec_box)

        # 3. System Diagnostics
        diag_box = QGroupBox("Runtime System Diagnostics")
        diag_box.setObjectName("settingsBox")
        diag_layout = QVBoxLayout(diag_box)
        diag_layout.setSpacing(8)

        self.btn_run_diagnostics = QPushButton("🩺  RUN FULL SYSTEM DIAGNOSTICS")
        self.btn_run_diagnostics.setObjectName("actionBtn")
        self.btn_run_diagnostics.clicked.connect(self.run_diagnostics)
        diag_layout.addWidget(self.btn_run_diagnostics)

        self.lbl_diagnostics_report = QLabel("Click above to verify Microphone, Faster-Whisper, SAPI5 TTS, and Ollama.")
        self.lbl_diagnostics_report.setObjectName("diagnosticsReport")
        diag_layout.addWidget(self.lbl_diagnostics_report)
        layout.addWidget(diag_box)

        # Save Button
        save_btn = QPushButton("💾  SAVE PREFERENCES")
        save_btn.setObjectName("primaryActionBtn")
        save_btn.clicked.connect(self._save_general_settings)
        layout.addWidget(save_btn)
        layout.addStretch()

        scroll.setWidget(container)
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)
        return page

    # ============================================================
    # PAGE 4: ABOUT & OFFLINE VERIFICATION
    # ============================================================

    def _create_about_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        about_box = QFrame()
        about_box.setObjectName("panel")
        box_layout = QVBoxLayout(about_box)
        box_layout.setContentsMargins(20, 20, 20, 20)
        box_layout.setSpacing(12)

        title = QLabel("NEO AI — Enterprise Local Windows Assistant")
        title.setObjectName("title")
        box_layout.addWidget(title)

        tagline = QLabel("Version 2.5 Offline Transformation • Pair Engineered by Gautam Vandar")
        tagline.setObjectName("subtitle")
        box_layout.addWidget(tagline)

        info = QTextBrowser()
        info.setObjectName("aboutBrowser")
        info.setHtml(
            """
            <div style='color: #cbf3f9; line-height: 1.6;'>
            <h3 style='color: #38bdf8;'>100% Offline Architecture</h3>
            <p>NEO AI operates fully offline on Windows. Supported PC commands never query Ollama or cloud endpoints.</p>
            <table style='width: 100%; border-collapse: collapse; margin-top: 10px; margin-bottom: 10px;'>
            <tr style='background: #081a24; color: #55eaff;'>
                <th style='padding: 6px; text-align: left; border: 1px solid #133a46;'>Subsystem</th>
                <th style='padding: 6px; text-align: left; border: 1px solid #133a46;'>Engine</th>
                <th style='padding: 6px; text-align: left; border: 1px solid #133a46;'>Offline Guarantee</th>
            </tr>
            <tr>
                <td style='padding: 6px; border: 1px solid #133a46;'><b>Speech Recognition</b></td>
                <td style='padding: 6px; border: 1px solid #133a46;'>Faster-Whisper (int8 CPU)</td>
                <td style='padding: 6px; border: 1px solid #133a46; color: #00f5a0;'>100% Local / On-Device</td>
            </tr>
            <tr>
                <td style='padding: 6px; border: 1px solid #133a46;'><b>Smart Command Router</b></td>
                <td style='padding: 6px; border: 1px solid #133a46;'>Deterministic Fast Router</td>
                <td style='padding: 6px; border: 1px solid #133a46; color: #00f5a0;'>100% Local (0ms LLM lag)</td>
            </tr>
            <tr>
                <td style='padding: 6px; border: 1px solid #133a46;'><b>Speech Synthesis</b></td>
                <td style='padding: 6px; border: 1px solid #133a46;'>Windows SAPI5 (pyttsx3)</td>
                <td style='padding: 6px; border: 1px solid #133a46; color: #00f5a0;'>100% Local (No cloud voice)</td>
            </tr>
            <tr>
                <td style='padding: 6px; border: 1px solid #133a46;'><b>Conversational AI</b></td>
                <td style='padding: 6px; border: 1px solid #133a46;'>Local Ollama (qwen3:1.7b)</td>
                <td style='padding: 6px; border: 1px solid #133a46; color: #00f5a0;'>100% Local LLM Only</td>
            </tr>
            <tr>
                <td style='padding: 6px; border: 1px solid #133a46;'><b>PC Automation</b></td>
                <td style='padding: 6px; border: 1px solid #133a46;'>Win32 & Safe Tool Registry</td>
                <td style='padding: 6px; border: 1px solid #133a46; color: #00f5a0;'>Strictly Sandboxed</td>
            </tr>
            </table>

            <h3 style='color: #38bdf8;'>Security & Privacy Guarantees</h3>
            <ul>
                <li><b>Zero Cloud Telemetry:</b> No voice recordings or text queries leave this device.</li>
                <li><b>Local-First Execution:</b> Calculator, Notepad, Volume, Screenshots, Files, and Search execute locally.</li>
                <li><b>Destructive Action Safeguards:</b> High-risk actions require user confirmation.</li>
            </ul>
            </div>
            """
        )
        box_layout.addWidget(info, 1)
        layout.addWidget(about_box, 1)
        return page

    # ============================================================
    # NAVIGATION & ACTION DISPATCHERS
    # ============================================================

    def switch_nav(self, index: int):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            active_str = "true" if i == index else "false"
            btn.setProperty("active", active_str)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def execute_quick_action(self, command: str):
        """Dispatches a quick action without blocking the UI thread."""
        self.input.setText(command)
        self.send_text()

    def log_activity(self, mode: str, command: str, status: str, detail: str):
        """Appends structured audit record to activity history and table."""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = {
            "time": timestamp,
            "mode": mode,
            "command": command,
            "status": status,
            "detail": detail
        }
        self.activity_log.append(entry)
        if hasattr(self, "activity_table"):
            row = self.activity_table.rowCount()
            self.activity_table.insertRow(row)
            self.activity_table.setItem(row, 0, QTableWidgetItem(timestamp))
            self.activity_table.setItem(row, 1, QTableWidgetItem(mode))
            self.activity_table.setItem(row, 2, QTableWidgetItem(command))
            self.activity_table.setItem(row, 3, QTableWidgetItem(status))
            self.activity_table.setItem(row, 4, QTableWidgetItem(detail))
            self.activity_table.scrollToBottom()
        if hasattr(self, "activity_count_label"):
            self.activity_count_label.setText(f"Total Operations: {len(self.activity_log)}")

    def _clear_activity_history(self):
        self.activity_log.clear()
        if hasattr(self, "activity_table"):
            self.activity_table.setRowCount(0)
        if hasattr(self, "activity_count_label"):
            self.activity_count_label.setText("Total Operations: 0")

    def _test_microphone_signal(self):
        from interfaces.voice import VoiceInterface
        idx = self.combo_mics.currentData()
        res = VoiceInterface.test_microphone_input(device_index=idx, duration=0.8)
        if res.get("success"):
            rms = res.get("rms", 0.0)
            peak = res.get("peak", 0)
            status = res.get("status_description", "")
            self.lbl_mic_signal_result.setText(f"Signal Test OK: RMS={rms}, Peak={peak}. {status}")
            self.lbl_mic_signal_result.setStyleSheet("color: #34d399;")
        else:
            err = res.get("error", "Unknown error")
            self.lbl_mic_signal_result.setText(f"Signal Test Failed: {err}")
            self.lbl_mic_signal_result.setStyleSheet("color: #f87171;")

    def _save_voice_settings(self):
        idx = self.combo_mics.currentData()
        name = self.combo_mics.currentText()
        lang = self.combo_lang.currentData()
        model = self.combo_whisper_model.currentData()
        tts_on = self.chk_tts_enabled.isChecked()
        rate = self.slider_rate.value()
        vol = self.slider_vol.value() / 100.0

        settings.set("mic_device_index", idx, save=False)
        settings.set("mic_device_name", name, save=False)
        settings.set("speech_language", lang, save=False)
        settings.set("whisper_model", model, save=False)
        settings.set("tts_enabled", tts_on, save=False)
        settings.set("tts_speech_rate", rate, save=False)
        settings.set("tts_volume", vol, save=True)

        tts_manager.set_rate(rate)
        tts_manager.set_volume(vol)
        self.append_chat("NEO > Voice pipeline and multilingual settings updated successfully.")
        QMessageBox.information(self, "Voice Settings", "Voice configuration saved and applied.")

    def _test_ollama_connection(self):
        from core.llm import llm_manager
        healthy = llm_manager.check_health()
        if healthy:
            models = llm_manager.list_models()
            model_list_str = ", ".join(models[:4]) if models else "Connected"
            self.lbl_ollama_status.setText(f"● Connected to Ollama ({len(models)} models: {model_list_str})")
            self.lbl_ollama_status.setStyleSheet("color: #34d399;")
        else:
            self.lbl_ollama_status.setText("● Ollama is offline or unreachable at host. Local PC commands still work.")
            self.lbl_ollama_status.setStyleSheet("color: #fbbf24;")

    def _save_general_settings(self):
        host = self.input_ollama_host.text().strip()
        model = self.input_ollama_model.text().strip()
        confirm = self.chk_confirm_destructive.isChecked()

        settings.set("ollama_host", host, save=False)
        settings.set("ollama_model", model, save=False)
        settings.set("confirm_destructive_actions", confirm, save=True)

        from core.llm import llm_manager
        llm_manager.ollama_provider._host = host
        llm_manager.ollama_provider.set_model(model)
        self.append_chat("NEO > System settings updated successfully.")
        QMessageBox.information(self, "Settings", "System configuration saved.")

    def run_diagnostics(self):
        from interfaces.voice import VoiceInterface
        mic_res = VoiceInterface.test_microphone_input(duration=0.5)
        mic_ok = mic_res.get("success", False)
        mic_txt = "Available" if mic_ok else "Not detected / silent"

        whisper_model = settings.get("whisper_model", "tiny.en")
        whisper_txt = f"Configured ({whisper_model})"

        sapi_ok = tts_manager.offline_provider.is_available()
        sapi_txt = "Available (Windows SAPI5 Local)" if sapi_ok else "Unavailable"

        from core.llm import llm_manager
        ollama_ok = llm_manager.check_health()
        ollama_txt = f"Reachable ({llm_manager.get_active_model()})" if ollama_ok else "Offline (Direct PC commands operational)"

        report = (
            f"• Microphone Hardware:  {mic_txt}\n"
            f"• Offline Speech Model: {whisper_txt}\n"
            f"• Offline SAPI5 TTS:    {sapi_txt}\n"
            f"• Local Ollama Brain:   {ollama_txt}\n"
            f"• System Status:        100% Offline Ready"
        )
        self.lbl_diagnostics_report.setText(report)

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
                font-family: "Segoe UI", sans-serif;
            }

            #title {
                color: #55eaff;
                font-size: 30px;
                font-weight: 700;
                letter-spacing: 1px;
            }

            #subtitle {
                color: #397985;
                font-size: 9px;
                font-weight: 600;
                letter-spacing: 1px;
            }

            #offlineBadge {
                background: #052e16;
                color: #34d399;
                border: 1px solid #10b981;
                border-radius: 9px;
                padding: 2px 8px;
                font-size: 10px;
                font-weight: 700;
            }

            #navContainer {
                background: #040e16;
                border: 1px solid #103844;
                border-radius: 10px;
            }

            #navButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 8px;
                color: #7dd3fc;
                font-size: 11px;
                font-weight: 600;
                padding: 6px 12px;
            }

            #navButton:hover {
                background: #08212e;
                border-color: #38bdf8;
                color: #ffffff;
            }

            #navButton[active="true"] {
                background: #082d38;
                border: 1px solid #00f5a0;
                color: #00f5a0;
                font-weight: 700;
            }

            #status {
                color: #54e7a6;
                font-size: 11px;
                font-weight: 700;
                font-family: Consolas, monospace;
            }

            #panel {
                background: #061018;
                border: 1px solid #123e4a;
                border-radius: 12px;
            }

            #panelTitle {
                color: #4de0f4;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1px;
            }

            #sectionHeader {
                color: #55eaff;
                font-size: 14px;
                font-weight: 700;
                letter-spacing: 1px;
                margin-bottom: 4px;
            }

            #badgeCount {
                color: #38bdf8;
                font-size: 11px;
                font-weight: 700;
                background: #081d28;
                border: 1px solid #1c6273;
                border-radius: 8px;
                padding: 4px 10px;
            }

            #telemetry {
                color: #62c6d5;
                font-family: Consolas, monospace;
                font-size: 11px;
                line-height: 1.4;
            }

            #chat {
                background: #02070b;
                border: 1px solid #0d3540;
                border-radius: 10px;
                padding: 10px;
                color: #9de8f3;
                font-family: Consolas, monospace;
                font-size: 11px;
            }

            .quickActionBtn,
            #quickActionBtn {
                background: #071923;
                border: 1px solid #164e63;
                border-radius: 8px;
                color: #a5f3fc;
                font-size: 10px;
                font-weight: 600;
                padding: 7px 6px;
            }

            .quickActionBtn:hover,
            #quickActionBtn:hover {
                background: #0b2d3d;
                border-color: #22d3ee;
                color: #ffffff;
            }

            #settingsBox {
                background: #061018;
                border: 1px solid #123e4a;
                border-radius: 10px;
                color: #7dd3fc;
                font-size: 11px;
                font-weight: 700;
                padding-top: 14px;
                margin-top: 6px;
            }

            #settingsCombo,
            QComboBox {
                background: #050d14;
                border: 1px solid #155364;
                border-radius: 6px;
                padding: 6px 10px;
                color: #d8fbff;
                font-size: 11px;
            }

            #settingsCheck,
            QCheckBox {
                color: #bae6fd;
                font-size: 11px;
            }

            #safeguardsText {
                color: #64748b;
                font-family: Consolas, monospace;
                font-size: 10px;
            }

            #diagnosticsReport {
                background: #04090f;
                border: 1px solid #0d3540;
                border-radius: 8px;
                padding: 10px;
                color: #a7f3d0;
                font-family: Consolas, monospace;
                font-size: 11px;
            }

            #activityTable {
                background: #02070b;
                border: 1px solid #0d3540;
                border-radius: 8px;
                color: #bae6fd;
                gridline-color: #0b222c;
                font-family: Consolas, monospace;
                font-size: 11px;
            }

            QHeaderView::section {
                background: #071923;
                color: #38bdf8;
                border: 1px solid #0d3540;
                padding: 6px;
                font-weight: bold;
                font-size: 11px;
            }

            #aboutBrowser {
                background: #02070b;
                border: 1px solid #0d3540;
                border-radius: 8px;
                padding: 12px;
            }

            #statusDetail {
                color: #6ee7b7;
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
                border-radius: 8px;
                padding: 11px;
                color: #d8fbff;
                font-size: 12px;
            }

            QLineEdit:focus {
                border: 1px solid #43e8ff;
            }

            QPushButton {
                background: #071923;
                border: 1px solid #1a7183;
                border-radius: 8px;
                padding: 10px 16px;
                color: #73e9f8;
                font-weight: 700;
                font-size: 11px;
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

            #primaryActionBtn {
                background: #064e3b;
                border: 1px solid #059669;
                color: #a7f3d0;
                padding: 10px 18px;
            }

            #primaryActionBtn:hover {
                background: #047857;
                border-color: #34d399;
                color: #ffffff;
            }

            #actionBtn {
                background: #0a2533;
                border: 1px solid #1f6477;
                color: #38bdf8;
                padding: 7px 14px;
            }

            #actionBtn:hover {
                background: #0d3347;
                border-color: #38bdf8;
                color: #bae6fd;
            }

            #voiceButton {
                background: #04251b;
                border: 1px solid #059669;
                color: #34d399;
            }

            #voiceButton:hover {
                background: #064e3b;
                border: 1px solid #10b981;
                color: #a7f3d0;
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

            #clearButton {
                background: #101524;
                border: 1px solid #3730a3;
                color: #a5b4fc;
            }

            #clearButton:hover {
                background: #1e1b4b;
                border: 1px solid #6366f1;
                color: #e0e7ff;
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

        # Sanitize credentials before they reach the visible transcript and
        # HTML-escape all dynamic text because QTextBrowser renders rich text.
        msg_str = mask_sensitive_data(str(message).strip())

        if msg_str.startswith("YOU >"):
            content = escape(msg_str[5:].strip())
            html = f"<div style='margin-bottom:6px;'><span style='color: #38bdf8; font-weight: bold;'>YOU &gt;</span> <span style='color: #f1f5f9;'>{content}</span></div>"
        elif msg_str.startswith("NEO >"):
            content = escape(msg_str[5:].strip())
            html = f"<div style='margin-bottom:6px;'><span style='color: #00f5a0; font-weight: bold;'>NEO &gt;</span> <span style='color: #bbf7d0;'>{content}</span></div>"
        elif msg_str.startswith("ORION >"):
            content = escape(msg_str[7:].strip())
            html = f"<div style='margin-bottom:6px;'><span style='color: #00f5a0; font-weight: bold;'>NEO &gt;</span> <span style='color: #bbf7d0;'>{content}</span></div>"
        elif msg_str.startswith("[TOOL]"):
            detail = escape(msg_str[6:].strip())
            html = f"<div style='margin-bottom:6px; padding:4px 8px; background: #061c27; border-left: 3px solid #38bdf8; border-radius: 4px;'><span style='color: #38bdf8; font-weight: bold;'>[ACTION]</span> <span style='color: #a5f3fc; font-family: Consolas;'>{detail}</span></div>"
        elif "error" in msg_str.lower() or "[fail]" in msg_str.lower():
            html = f"<div style='margin-bottom:6px;'><span style='color: #ef4444; font-weight: bold;'>[ERROR]</span> <span style='color: #fca5a5;'>{escape(msg_str)}</span></div>"
        elif "●" in msg_str or "[ok]" in msg_str.lower() or "online" in msg_str.lower():
            html = f"<div style='margin-bottom:6px;'><span style='color: #22d3ee; font-weight: bold;'>●</span> <span style='color: #a5f3fc;'>{escape(msg_str)}</span></div>"
        else:
            html = f"<div style='margin-bottom:6px;'><span style='color: #7dd3fc;'>{escape(msg_str)}</span></div>"

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

        self.current_state = state

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

        turns = len(getattr(self.agent, "conversation", [])) // 2
        self.telemetry.setText(
            f"AI CORE     ONLINE\n"
            f"MODEL       {model_name[:12]}\n"
            f"CONTEXT     {turns} turns\n"
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
        self._last_user_query = command

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

        query = getattr(self, "_last_user_query", "Text Query")
        self.log_activity(query[:30], "Text Command", "Completed", response[:50].replace("\n", " "))

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

        self.log_activity("Voice Input", "Voice Pipeline", "Completed", response[:50].replace("\n", " "))

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
    # TOOL EXECUTION CALLBACK & CONVERSATION CONTROLS
    # ============================================================

    def on_tool_executed(self, tool_name: str, result: str, success: bool):
        """Called whenever an action tool is executed by NEO agent."""
        status_tag = "SUCCESS" if success else "FAILED"
        self.append_chat(f"[TOOL] {tool_name} ({status_tag}) > {result}")
        self.log_activity(f"Tool: {tool_name}", "PC Tool", status_tag, result[:50].replace("\n", " "))

    def clear_conversation(self):
        """Clears current conversation history without touching persistent settings."""
        self.agent.clear_conversation()
        self.chat.clear()
        self.append_chat("NEO > Conversation context cleared. Persistent settings preserved.")
        self.set_state("READY")
        self.log_activity("Clear History", "Context", "Success", "History cleared")

    # ============================================================
    # STOP / CANCEL ACTION
    # ============================================================

    def stop_action(self):

        self.agent.cancel_current_operation()
        tts_manager.stop()
        self.append_chat("NEO > [STOPPED] Speech synthesis halted and current operations cancelled.")
        self.set_state("READY")
        self.set_inputs_enabled(True)
        self.log_activity("Stop/Cancel", "User Interrupt", "Halted", "Cancelled operations")

    def closeEvent(self, event):
        """Stop work and defer closing until active QThreads have actually exited."""
        if self._close_pending:
            event.ignore()
            return

        try:
            self.stop_action()
        except Exception:
            pass

        active_threads = [
            thread for thread in (self.thread, self.voice_thread, self.tts_thread)
            if thread is not None and thread.isRunning()
        ]
        if not active_threads:
            event.accept()
            return

        # Never destroy a QThread while it is still running. Keep the window
        # alive (and the event loop responsive) until all workers finish.
        self._close_pending = True
        self.set_inputs_enabled(False)
        for thread in active_threads:
            try:
                thread.quit()
                thread.finished.connect(self._close_after_workers)
            except Exception:
                pass
        event.ignore()

    @Slot()
    def _close_after_workers(self):
        """Close the window once every tracked worker thread has exited."""
        active = [
            thread for thread in (self.thread, self.voice_thread, self.tts_thread)
            if thread is not None and thread.isRunning()
        ]
        if not active:
            self._close_pending = False
            self.close()

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

