"""
NEO AI - Settings & Diagnostics Dialog
Provides user configuration for AI brain, speech recognition,
microphones, natural & offline TTS, audio output routing, and system diagnostics.
"""

import os
import psutil
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QSlider,
    QMessageBox,
    QTextEdit,
    QGroupBox,
    QFormLayout
)

from core.settings import settings
from core.llm import llm_manager
from interfaces.voice import VoiceInterface
from interfaces.tts import TTSManager, SUPPORTED_NEURAL_VOICES, tts_manager


class TestVoiceWorker(QThread):
    finished_signal = Signal(str)

    def __init__(
        self,
        text: str,
        voice_online: str,
        provider: str,
        rate: int = 180,
        volume: float = 1.0,
        output_device: Optional[int] = None
    ):
        super().__init__()
        self.text = text
        self.voice_online = voice_online
        self.provider = provider
        self.rate = rate
        self.volume = volume
        self.output_device = output_device

    def run(self):
        try:
            try:
                import pythoncom
                pythoncom.CoInitialize()
            except Exception:
                pass

            mgr = TTSManager()
            mgr.set_rate(self.rate)
            mgr.set_volume(self.volume)
            mgr.set_output_device(self.output_device)
            if self.provider == "online":
                mgr.set_online_voice(self.voice_online)

            success = mgr.speak(self.text)
            if success:
                self.finished_signal.emit(f"Audio playback successful ({self.voice_online}).")
            else:
                self.finished_signal.emit("Playback interrupted or stopped.")
        except Exception as exc:
            self.finished_signal.emit(f"TTS Error: {exc}")


class SettingsDialog(QDialog):
    """Complete Settings and Diagnostics modal for NEO AI."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("NEO AI — Settings & Diagnostics")
        self.resize(740, 600)
        self.setMinimumSize(660, 520)

        self.test_worker: Optional[TestVoiceWorker] = None

        self._build_ui()
        self._load_current_values()
        self._apply_style()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        title = QLabel("NEO AI CONFIGURATION & DIAGNOSTICS")
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)

        # Tabs
        self._build_ai_tab()
        self._build_voice_tab()
        self._build_diagnostics_tab()

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_save = QPushButton("SAVE & APPLY")
        self.btn_save.setObjectName("saveButton")
        self.btn_save.clicked.connect(self._save_and_close)

        self.btn_cancel = QPushButton("CANCEL")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

    # ============================================================
    # TAB 1: AI BRAIN
    # ============================================================

    def _build_ai_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(14)

        # Provider Selection
        group_provider = QGroupBox("Active AI Engine")
        form_provider = QFormLayout(group_provider)

        self.combo_ai_provider = QComboBox()
        self.combo_ai_provider.addItems(["ollama", "cloud"])
        form_provider.addRow("Provider:", self.combo_ai_provider)
        layout.addWidget(group_provider)

        # Ollama Group
        group_ollama = QGroupBox("Local Ollama Configuration")
        form_ollama = QFormLayout(group_ollama)

        self.input_ollama_host = QLineEdit()
        form_ollama.addRow("Host URL:", self.input_ollama_host)

        model_row = QHBoxLayout()
        self.combo_ollama_model = QComboBox()
        self.btn_refresh_models = QPushButton("🔄 Refresh")
        self.btn_refresh_models.clicked.connect(self._refresh_ollama_models)
        model_row.addWidget(self.combo_ollama_model, 1)
        model_row.addWidget(self.btn_refresh_models)
        form_ollama.addRow("Installed Models:", model_row)

        layout.addWidget(group_ollama)

        # Cloud LLM Group
        group_cloud = QGroupBox("Optional Cloud LLM (OpenAI-Compatible)")
        form_cloud = QFormLayout(group_cloud)

        self.input_cloud_url = QLineEdit()
        form_cloud.addRow("API Base URL:", self.input_cloud_url)

        self.input_cloud_key = QLineEdit()
        self.input_cloud_key.setEchoMode(QLineEdit.Password)
        self.input_cloud_key.setPlaceholderText("sk-...")
        form_cloud.addRow("API Key:", self.input_cloud_key)

        self.input_cloud_model = QLineEdit()
        form_cloud.addRow("Model Name:", self.input_cloud_model)

        layout.addWidget(group_cloud)
        layout.addStretch()

        self.tabs.addTab(tab, "🧠 AI Brain")

    # ============================================================
    # TAB 2: VOICE & AUDIO
    # ============================================================

    def _build_voice_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(14)

        # Speech Recognition Group
        group_asr = QGroupBox("Speech Recognition (Faster-Whisper)")
        form_asr = QFormLayout(group_asr)

        self.combo_whisper_model = QComboBox()
        self.combo_whisper_model.addItems(["tiny.en", "tiny", "base", "small"])
        form_asr.addRow("Model Size:", self.combo_whisper_model)

        self.combo_speech_lang = QComboBox()
        self.combo_speech_lang.addItem("English", "en")
        self.combo_speech_lang.addItem("Hindi", "hi")
        self.combo_speech_lang.addItem("Gujarati", "gu")
        self.combo_speech_lang.addItem("Auto Detect", "auto")
        self.combo_speech_lang.currentIndexChanged.connect(self._on_language_changed)
        form_asr.addRow("Language:", self.combo_speech_lang)

        # Microphone Selection
        mic_row = QHBoxLayout()
        self.combo_microphone = QComboBox()
        self.btn_test_mic = QPushButton("🎤 Test Mic")
        self.btn_test_mic.clicked.connect(self._test_microphone)
        mic_row.addWidget(self.combo_microphone, 1)
        mic_row.addWidget(self.btn_test_mic)
        form_asr.addRow("Input Device:", mic_row)

        layout.addWidget(group_asr)

        # Text to Speech Group
        group_tts = QGroupBox("Speech Synthesis (Natural & Offline Fallback)")
        form_tts = QFormLayout(group_tts)

        self.combo_tts_mode = QComboBox()
        self.combo_tts_mode.addItem("Online Neural (edge-tts)", "online")
        self.combo_tts_mode.addItem("Offline SAPI5 (pyttsx3)", "offline")
        form_tts.addRow("Primary Mode:", self.combo_tts_mode)

        self.combo_online_voice = QComboBox()
        form_tts.addRow("Neural Voice:", self.combo_online_voice)

        # Audio Output Routing
        out_row = QHBoxLayout()
        self.combo_output_device = QComboBox()
        self.btn_refresh_outputs = QPushButton("🔄 Refresh")
        self.btn_refresh_outputs.clicked.connect(self._refresh_output_devices)
        out_row.addWidget(self.combo_output_device, 1)
        out_row.addWidget(self.btn_refresh_outputs)
        form_tts.addRow("Output Device:", out_row)

        # Speech Rate
        rate_row = QHBoxLayout()
        self.slider_rate = QSlider(Qt.Horizontal)
        self.slider_rate.setRange(120, 260)
        self.lbl_rate_val = QLabel("180 WPM (Normal)")
        self.lbl_rate_val.setStyleSheet("color: #38bdf8; font-weight: bold; min-width: 120px;")
        self.slider_rate.valueChanged.connect(self._on_rate_slider_changed)
        rate_row.addWidget(self.slider_rate, 1)
        rate_row.addWidget(self.lbl_rate_val)
        form_tts.addRow("Speech Rate:", rate_row)

        # Volume
        vol_row = QHBoxLayout()
        self.slider_vol = QSlider(Qt.Horizontal)
        self.slider_vol.setRange(0, 100)
        self.lbl_vol_val = QLabel("100%")
        self.lbl_vol_val.setStyleSheet("color: #38bdf8; font-weight: bold; min-width: 120px;")
        self.slider_vol.valueChanged.connect(self._on_vol_slider_changed)
        vol_row.addWidget(self.slider_vol, 1)
        vol_row.addWidget(self.lbl_vol_val)
        form_tts.addRow("Volume:", vol_row)

        # Provider Status
        self.lbl_provider_status = QLabel("● Provider Status: Ready")
        self.lbl_provider_status.setStyleSheet("color: #54e7a6; font-size: 11px; font-weight: 600;")
        form_tts.addRow("Status:", self.lbl_provider_status)

        # Test Voice & Stop Buttons
        btn_test_row = QHBoxLayout()
        self.btn_test_voice = QPushButton("🔊 Test Voice Output")
        self.btn_test_voice.clicked.connect(self._test_voice)
        self.btn_stop_voice = QPushButton("⏹ Stop Speaking")
        self.btn_stop_voice.clicked.connect(self._stop_test_voice)
        btn_test_row.addStretch()
        btn_test_row.addWidget(self.btn_test_voice)
        btn_test_row.addWidget(self.btn_stop_voice)
        form_tts.addRow("", btn_test_row)

        layout.addWidget(group_tts)
        layout.addStretch()

        self.tabs.addTab(tab, "🎙 Voice & Audio")

    # ============================================================
    # TAB 3: DIAGNOSTICS & LOGS
    # ============================================================

    def _build_diagnostics_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        info_label = QLabel("Real-Time Hardware & Subsystem Telemetry:")
        info_label.setObjectName("subTitle")
        layout.addWidget(info_label)

        self.txt_diagnostics = QTextEdit()
        self.txt_diagnostics.setReadOnly(True)
        self.txt_diagnostics.setObjectName("diagConsole")
        layout.addWidget(self.txt_diagnostics, 1)

        btn_refresh_diag = QPushButton("🔄 Refresh Diagnostics")
        btn_refresh_diag.clicked.connect(self._update_diagnostics)
        layout.addWidget(btn_refresh_diag)

        self.tabs.addTab(tab, "📊 Diagnostics")

    # ============================================================
    # VALUES & REFRESH
    # ============================================================

    def _load_current_values(self):
        # AI
        provider = settings.get("ai_provider", "ollama")
        idx = self.combo_ai_provider.findText(provider)
        if idx >= 0:
            self.combo_ai_provider.setCurrentIndex(idx)

        self.input_ollama_host.setText(settings.get("ollama_host", "http://127.0.0.1:11434"))
        self._refresh_ollama_models()

        self.input_cloud_url.setText(settings.get("cloud_base_url", "https://api.openai.com/v1"))
        self.input_cloud_key.setText(settings.get("cloud_api_key", ""))
        self.input_cloud_model.setText(settings.get("cloud_model", "gpt-4o-mini"))

        # Voice & Language
        whisper_m = settings.get("whisper_model", "tiny.en")
        idx = self.combo_whisper_model.findText(whisper_m)
        if idx >= 0:
            self.combo_whisper_model.setCurrentIndex(idx)

        lang = settings.get("speech_language", "en")
        idx = self.combo_speech_lang.findData(lang)
        if idx >= 0:
            self.combo_speech_lang.setCurrentIndex(idx)

        # Populate and filter voices according to current language
        self._filter_voices_by_language(lang)

        # Microphones & Outputs
        self._refresh_microphones()
        self._refresh_output_devices()

        # TTS Primary Mode
        tts_mode = settings.get("tts_provider", "online")
        idx = self.combo_tts_mode.findData(tts_mode)
        if idx >= 0:
            self.combo_tts_mode.setCurrentIndex(idx)

        # Sliders
        rate_val = int(settings.get("tts_speech_rate", 180))
        self.slider_rate.setValue(rate_val)
        self._on_rate_slider_changed(rate_val)

        vol_val = int(settings.get("tts_volume", 1.0) * 100)
        self.slider_vol.setValue(vol_val)
        self._on_vol_slider_changed(vol_val)

        # Live provider status check
        status = tts_manager.get_status()
        self.lbl_provider_status.setText(f"● Active Provider: {status.get('provider', 'Online Neural')}")

        # Run diagnostics update
        self._update_diagnostics()

    def _on_language_changed(self, index: int):
        lang = self.combo_speech_lang.currentData()
        self._filter_voices_by_language(lang)

        # Suggest multilingual Whisper model if user switches to non-English
        if lang in {"hi", "gu", "auto"} and self.combo_whisper_model.currentText() == "tiny.en":
            idx = self.combo_whisper_model.findText("tiny")
            if idx >= 0:
                self.combo_whisper_model.setCurrentIndex(idx)

    def _filter_voices_by_language(self, lang_code: str):
        self.combo_online_voice.blockSignals(True)
        self.combo_online_voice.clear()

        if lang_code in SUPPORTED_NEURAL_VOICES:
            voice_list = SUPPORTED_NEURAL_VOICES[lang_code]
        else:
            # Auto / all languages
            voice_list = [v for sublist in SUPPORTED_NEURAL_VOICES.values() for v in sublist]

        for label, voice_name in voice_list:
            self.combo_online_voice.addItem(label, voice_name)

        # Restore saved voice if it exists in the filtered list
        current = settings.get("tts_voice_online", "en-US-AriaNeural")
        idx = self.combo_online_voice.findData(current)
        if idx >= 0:
            self.combo_online_voice.setCurrentIndex(idx)
        else:
            self.combo_online_voice.setCurrentIndex(0)

        self.combo_online_voice.blockSignals(False)

    def _on_rate_slider_changed(self, value: int):
        status = "Normal" if value == 180 else ("Fast" if value > 180 else "Slow")
        self.lbl_rate_val.setText(f"{value} WPM ({status})")

    def _on_vol_slider_changed(self, value: int):
        self.lbl_vol_val.setText(f"{value}%")

    def _refresh_ollama_models(self):
        self.combo_ollama_model.clear()
        models = llm_manager.ollama_provider.list_models()
        if models:
            self.combo_ollama_model.addItems(models)
            current = settings.get("ollama_model", "")
            idx = self.combo_ollama_model.findText(current)
            if idx >= 0:
                self.combo_ollama_model.setCurrentIndex(idx)
        else:
            self.combo_ollama_model.addItem("Ollama offline or no models found")

    def _refresh_microphones(self):
        self.combo_microphone.clear()
        self.combo_microphone.addItem("System Default Device", None)
        mics = VoiceInterface.get_available_microphones()
        configured_mic = settings.get("mic_device_index")

        selected_idx = 0
        for i, (idx, name) in enumerate(mics, 1):
            self.combo_microphone.addItem(f"[{idx}] {name}", idx)
            if configured_mic is not None and configured_mic == idx:
                selected_idx = i

        self.combo_microphone.setCurrentIndex(selected_idx)

    def _refresh_output_devices(self):
        self.combo_output_device.clear()
        self.combo_output_device.addItem("System Default Output", None)
        outputs = TTSManager.get_available_output_devices()
        configured_out = settings.get("tts_output_device_index")

        selected_idx = 0
        for i, (idx, label) in enumerate(outputs, 1):
            self.combo_output_device.addItem(label, idx)
            if configured_out is not None and configured_out == idx:
                selected_idx = i

        self.combo_output_device.setCurrentIndex(selected_idx)

    def _test_microphone(self):
        device_idx = self.combo_microphone.currentData()
        try:
            import speech_recognition as sr
            with sr.Microphone(device_index=device_idx) as src:
                r = sr.Recognizer()
                r.adjust_for_ambient_noise(src, duration=0.2)
            QMessageBox.information(
                self,
                "Microphone Check",
                f"Microphone {self.combo_microphone.currentText()} is accessible and online!"
            )
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Microphone Error",
                f"Failed to open microphone: {exc}"
            )

    def _test_voice(self):
        provider = self.combo_tts_mode.currentData()
        voice_online = self.combo_online_voice.currentData()
        rate = self.slider_rate.value()
        volume = self.slider_vol.value() / 100.0
        output_device = self.combo_output_device.currentData()

        # Language-specific natural sample phrase
        lang = self.combo_speech_lang.currentData()
        test_phrases = {
            "en": "Hello! NEO AI natural voice synthesis is operational.",
            "hi": "नमस्ते! नियो एआई का आवाज़ सिस्टम पूरी तरह सक्रिय है।",
            "gu": "નમસ્તે! નિયો એઆઈ નું અવાજ સિસ્ટમ પીસી પર સંપૂર્ણ સક્રિય છે.",
        }
        text = test_phrases.get(lang, "Hello! NEO AI natural voice synthesis is operational.")

        self.btn_test_voice.setEnabled(False)
        self.lbl_provider_status.setText(f"● Testing playback via {provider}...")
        self.test_worker = TestVoiceWorker(
            text=text,
            voice_online=voice_online,
            provider=provider,
            rate=rate,
            volume=volume,
            output_device=output_device
        )
        self.test_worker.finished_signal.connect(self._on_test_voice_done)
        self.test_worker.start()

    def _stop_test_voice(self):
        tts_manager.stop()
        self.btn_test_voice.setEnabled(True)
        self.lbl_provider_status.setText("● Playback stopped by user.")

    def _on_test_voice_done(self, msg: str):
        self.btn_test_voice.setEnabled(True)
        if "Error" in msg:
            self.lbl_provider_status.setText("● [ERROR] Playback failed.")
            self.lbl_provider_status.setStyleSheet("color: #ef4444; font-size: 11px; font-weight: 600;")
            QMessageBox.warning(self, "Voice Test", msg)
        else:
            self.lbl_provider_status.setText("● Playback verified successfully.")
            self.lbl_provider_status.setStyleSheet("color: #54e7a6; font-size: 11px; font-weight: 600;")
            QMessageBox.information(self, "Voice Test", msg)

    def _update_diagnostics(self):
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory()
        battery = psutil.sensors_battery()
        batt_info = f"{battery.percent}%" if battery else "AC Power"

        ollama_ok = llm_manager.ollama_provider.check_health()
        mics_count = len(VoiceInterface.get_available_microphones())
        outs_count = len(TTSManager.get_available_output_devices())

        report = f"""==================================================
  NEO AI — SYSTEM & SUBSYSTEM TELEMETRY
==================================================
Host OS:           Windows ({os.name})
CPU Utilization:   {cpu}%
System Memory:     {mem.percent}% ({round(mem.used / 1024**3, 1)} GB / {round(mem.total / 1024**3, 1)} GB)
Power State:       {batt_info}

AI Brain:
  Ollama Engine:   {'ONLINE' if ollama_ok else 'UNAVAILABLE'}
  Active Provider: {llm_manager.get_provider().provider_name}

Voice Subsystems:
  Input Devices:   {mics_count} microphone(s) detected
  Output Devices:  {outs_count} speaker/headphone output(s) detected
  Speech Engine:   Faster-Whisper ({settings.get('whisper_model', 'tiny.en')})
  Language Target: {settings.get('speech_language', 'en').upper()}
  TTS Mode:        {settings.get('tts_provider', 'online')}
  Online Voice:    {settings.get('tts_voice_online', 'en-US-AriaNeural')}

Security & Control:
  Path Guard:      Active (Root/System traversal blocked)
  Confirm Actions: {settings.get('confirm_destructive_actions', True)}
=================================================="""
        self.txt_diagnostics.setText(report)

    def _save_and_close(self):
        # Update settings
        settings.set("ai_provider", self.combo_ai_provider.currentText())
        settings.set("ollama_host", self.input_ollama_host.text().strip())

        ollama_m = self.combo_ollama_model.currentText()
        if "offline" not in ollama_m.lower():
            settings.set("ollama_model", ollama_m)
            llm_manager.ollama_provider.set_model(ollama_m)

        settings.set("cloud_base_url", self.input_cloud_url.text().strip())
        settings.set("cloud_api_key", self.input_cloud_key.text().strip())
        settings.set("cloud_model", self.input_cloud_model.text().strip())

        settings.set("whisper_model", self.combo_whisper_model.currentText())
        settings.set("speech_language", self.combo_speech_lang.currentData())
        settings.set("mic_device_index", self.combo_microphone.currentData())

        settings.set("tts_provider", self.combo_tts_mode.currentData())
        settings.set("tts_voice_online", self.combo_online_voice.currentData())
        settings.set("tts_output_device_index", self.combo_output_device.currentData())
        settings.set("tts_speech_rate", self.slider_rate.value())
        settings.set("tts_volume", self.slider_vol.value() / 100.0)

        # Apply immediately to global tts_manager instance
        tts_manager.set_online_voice(self.combo_online_voice.currentData())
        tts_manager.set_output_device(self.combo_output_device.currentData())
        tts_manager.set_rate(self.slider_rate.value())
        tts_manager.set_volume(self.slider_vol.value() / 100.0)

        settings.save()
        self.accept()

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog {
                background: #02070c;
                color: #bff7ff;
                font-family: "Segoe UI", sans-serif;
            }
            #dialogTitle {
                color: #55eaff;
                font-size: 16px;
                font-weight: 700;
                letter-spacing: 1px;
            }
            #subTitle {
                color: #38bdf8;
                font-size: 13px;
                font-weight: 600;
            }
            QTabWidget::pane {
                border: 1px solid #123e4a;
                background: #061018;
                border-radius: 8px;
            }
            QTabBar::tab {
                background: #050d14;
                color: #7dd3fc;
                padding: 10px 18px;
                border: 1px solid #0f303a;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background: #061018;
                color: #00f5a0;
                font-weight: bold;
                border-color: #123e4a;
            }
            QGroupBox {
                border: 1px solid #133945;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
                font-weight: 600;
                color: #38bdf8;
            }
            QLineEdit, QComboBox {
                background: #02070b;
                border: 1px solid #1a5666;
                border-radius: 6px;
                padding: 7px 10px;
                color: #f1f5f9;
                font-size: 12px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #00f5a0;
            }
            QPushButton {
                background: #071f2b;
                border: 1px solid #1c6273;
                border-radius: 6px;
                padding: 8px 16px;
                color: #73e9f8;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #0c3347;
                border: 1px solid #38bdf8;
                color: #bae6fd;
            }
            #saveButton {
                background: #064e3b;
                border: 1px solid #00f5a0;
                color: #ecfdf5;
            }
            #saveButton:hover {
                background: #047857;
                color: #ffffff;
            }
            #diagConsole {
                background: #02070b;
                border: 1px solid #0d3540;
                border-radius: 6px;
                color: #67e8f9;
                font-family: Consolas, monospace;
                font-size: 11px;
                padding: 10px;
            }
        """)
