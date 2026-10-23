"""
NEO AI - Voice Interface Pipeline
Coordinates audio capture, speech recognition, assistant execution,
and natural text-to-speech with automatic offline fallback.
"""

import os
import tempfile
from typing import Callable, Optional, Tuple, List

import speech_recognition as sr
from faster_whisper import WhisperModel

# Ensure PyAV metadata_errors compatibility
try:
    import av
    _orig_av_open = av.open

    def _safe_av_open(*args, **kwargs):
        kwargs.pop("metadata_errors", None)
        return _orig_av_open(*args, **kwargs)

    av.open = _safe_av_open
except Exception:
    pass

from config import MICROPHONE_INDEX
from core.settings import settings
from interfaces.tts import TTSManager


class VoiceInterface:
    """Manages audio capture, Whisper transcription, and TTS playback."""

    def __init__(
        self,
        agent,
        output_callback: Optional[Callable[[str], None]] = None,
        state_callback: Optional[Callable[[str], None]] = None
    ):
        self.agent = agent
        self.output_callback = output_callback or print
        self.state_callback = state_callback or (lambda *_: None)

        # Audio Capture
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 250
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 1.15
        self.recognizer.non_speaking_duration = 0.45
        self.recognizer.phrase_threshold = 0.20

        # Faster-Whisper Model
        self.whisper_model: Optional[WhisperModel] = None
        self.whisper_ready: bool = False
        self._current_whisper_model_name: Optional[str] = None
        self._load_whisper_model()

        # Text-to-Speech Manager (Online Neural + Offline SAPI Fallback)
        self.tts_manager = TTSManager(log_callback=self.output)

        # Backward compatibility for pyttsx3 engine references
        self.engine = getattr(self.tts_manager.offline_provider, "_engine", None)

    # ============================================================
    # WHISPER MANAGEMENT
    # ============================================================

    def _load_whisper_model(self, model_name: Optional[str] = None):
        """Loads or reloads Faster-Whisper model, selecting multilingual model if needed."""
        target_model = model_name or settings.get("whisper_model", "tiny.en")
        lang_setting = settings.get("speech_language", "en")

        # Automatically select multilingual model if language is Hindi, Gujarati, or Auto
        if lang_setting in {"hi", "gu", "auto"} and target_model.endswith(".en"):
            target_model = "tiny"
            settings.set("whisper_model", "tiny")

        if self.whisper_ready and self._current_whisper_model_name == target_model:
            return

        self.output(f"NEO > Initializing local Whisper model ({target_model})...")
        try:
            self.whisper_model = WhisperModel(
                target_model,
                device="cpu",
                compute_type="int8",
                cpu_threads=4
            )
            self.whisper_ready = True
            self._current_whisper_model_name = target_model
            self.output(f"NEO > Local Whisper ({target_model}) ready.")
        except Exception as exc:
            self.whisper_model = None
            self.whisper_ready = False
            self.output(f"NEO > Whisper initialization failed: {exc}")

    # ============================================================
    # MICROPHONE DIAGNOSTICS
    # ============================================================

    @staticmethod
    def get_available_microphones() -> List[Tuple[int, str]]:
        """Returns indexed list of available audio input devices."""
        try:
            names = sr.Microphone.list_microphone_names()
            return [(idx, name) for idx, name in enumerate(names)]
        except Exception:
            return []

    # ============================================================
    # OUTPUT & STATE
    # ============================================================

    def output(self, message: str):
        try:
            self.output_callback(str(message))
        except Exception:
            print(message)

    def state(self, value: str):
        try:
            self.state_callback(str(value))
        except Exception:
            pass

    # ============================================================
    # SPEAK & PLAYBACK
    # ============================================================

    def speak(self, text: str):
        """Speaks text using active provider with offline fallback."""
        if not text:
            return

        self.state("SPEAKING")
        self.output(f"NEO > {text}")

        def _on_start():
            self.state("SPEAKING")

        def _on_done():
            self.state("READY")

        try:
            self.tts_manager.speak(text, on_start=_on_start, on_done=_on_done)
        except Exception as exc:
            self.output(f"NEO > TTS playback error: {exc}")

        self.state("READY")

    def stop_speaking(self):
        """Immediately interrupts speech synthesis and audio output."""
        self.tts_manager.stop()
        self.state("READY")

    # ============================================================
    # AUDIO -> TEMP WAV
    # ============================================================

    def _audio_to_wav(self, audio: sr.AudioData) -> str:
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_path = temp_file.name
        temp_file.close()

        try:
            wav_data = audio.get_wav_data()
            with open(temp_path, "wb") as f:
                f.write(wav_data)
            return temp_path
        except Exception:
            try:
                os.remove(temp_path)
            except Exception:
                pass
            raise

    # ============================================================
    # WHISPER TRANSCRIPTION
    # ============================================================

    def _transcribe(self, wav_path: str) -> Optional[str]:
        if not self.whisper_ready or self.whisper_model is None:
            return None

        try:
            try:
                import soundfile as sf
                audio_input, _ = sf.read(wav_path, dtype="float32")
            except Exception:
                audio_input = wav_path

            # Language selection from settings
            lang_setting = settings.get("speech_language", "en")
            language = None if lang_setting in {"auto", None, ""} else lang_setting

            # Check if language requires multilingual model
            if lang_setting in {"hi", "gu", "auto"} and self._current_whisper_model_name and self._current_whisper_model_name.endswith(".en"):
                self._load_whisper_model("tiny")

            segments, info = self.whisper_model.transcribe(
                audio_input,
                language=language,
                beam_size=1,
                best_of=1,
                temperature=0,
                vad_filter=False,
                condition_on_previous_text=False
            )

            detected_lang = getattr(info, "language", None)
            prob = getattr(info, "language_probability", 1.0)
            if detected_lang:
                self.output(f"NEO > [ASR] Detected language: {detected_lang.upper()} ({prob:.0%})")

            text_parts = [seg.text.strip() for seg in segments if seg.text.strip()]
            return " ".join(text_parts).strip()

        except Exception as exc:
            self.output(f"NEO > Whisper error: {exc}")
            return None

    # ============================================================
    # LISTEN
    # ============================================================

    def listen_once(self) -> Optional[str]:
        self.state("LISTENING")
        wav_path = None

        # Check available microphones
        mics = self.get_available_microphones()
        if not mics:
            self.state("ERROR")
            self.output("NEO > [ERROR] No microphone devices detected.")
            return None

        # Determine configured device index
        device_index = settings.get("mic_device_index", MICROPHONE_INDEX)

        try:
            with sr.Microphone(device_index=device_index) as source:
                self.output("NEO > ● LISTENING")

                try:
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.10)
                except Exception:
                    pass

                self.output("NEO > Speak now...")
                audio = self.recognizer.listen(
                    source,
                    timeout=8,
                    phrase_time_limit=20
                )

            self.output("NEO > Speech captured.")
            self.state("THINKING")
            self.output("NEO > Transcribing locally...")

            wav_path = self._audio_to_wav(audio)
            text = self._transcribe(wav_path)

            if not text:
                self.output("NEO > I couldn't understand that.")
                self.state("READY")
                return None

            self.output(f"YOU > {text}")
            return text

        except sr.WaitTimeoutError:
            self.output("NEO > No speech detected.")
        except Exception as exc:
            self.state("ERROR")
            self.output(f"NEO > Voice capture error: {exc}")
        finally:
            if wav_path and os.path.exists(wav_path):
                try:
                    os.remove(wav_path)
                except Exception:
                    pass

        self.state("READY")
        return None

    # ============================================================
    # PROCESS COMMAND
    # ============================================================

    def process_voice_command(self) -> Optional[str]:
        command = self.listen_once()
        if not command:
            return None

        try:
            self.state("THINKING")
            self.output("NEO > Thinking...")

            response = self.agent.run(command)
            if response is None:
                response = "Command completed."

            self.speak(response)
            return response

        except Exception as exc:
            self.state("READY")
            self.output(f"NEO > Agent error: {exc}")
            return None