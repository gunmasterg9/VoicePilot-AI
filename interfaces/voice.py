"""
NEO AI - Voice Interface Pipeline
Coordinates audio capture, speech recognition, assistant execution,
and natural text-to-speech with automatic offline fallback.
"""

import os
import tempfile
from typing import Callable, Optional, Tuple, List, Dict, Any

import numpy as np
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

# Module-level cache for Faster-Whisper models to prevent redundant reloads across worker runs
_GLOBAL_WHISPER_CACHE: Dict[str, WhisperModel] = {}

VIRTUAL_DEVICE_KEYWORDS = [
    "virtual", "cable", "stereomix", "stereo mix", "audiorelay", "streamer", "mapper"
]


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

        # Audio Capture Recognizer
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = int(settings.get("mic_energy_threshold", 300))
        self.recognizer.dynamic_energy_threshold = bool(settings.get("mic_dynamic_energy", True))
        self.recognizer.dynamic_energy_adjustment_damping = 0.15
        self.recognizer.dynamic_energy_ratio = 1.5
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
    # WHISPER MANAGEMENT (CACHED)
    # ============================================================

    def _load_whisper_model(self, model_name: Optional[str] = None):
        """Loads or retrieves cached Faster-Whisper model, selecting multilingual model if needed."""
        target_model = model_name or settings.get("whisper_model", "tiny.en")
        lang_setting = settings.get("speech_language", "en")

        # Automatically select multilingual model if language is Hindi, Gujarati, or Auto
        if lang_setting in {"hi", "gu", "auto"} and target_model.endswith(".en"):
            target_model = "tiny"
            settings.set("whisper_model", "tiny")

        if self.whisper_ready and self._current_whisper_model_name == target_model:
            return

        # Check global cache first
        if target_model in _GLOBAL_WHISPER_CACHE:
            self.whisper_model = _GLOBAL_WHISPER_CACHE[target_model]
            self.whisper_ready = True
            self._current_whisper_model_name = target_model
            self.output(f"NEO > Local Whisper ({target_model}) ready (cached).")
            return

        self.output(f"NEO > Initializing local Whisper model ({target_model})...")
        try:
            model = WhisperModel(
                target_model,
                device="cpu",
                compute_type="int8",
                cpu_threads=4
            )
            _GLOBAL_WHISPER_CACHE[target_model] = model
            self.whisper_model = model
            self.whisper_ready = True
            self._current_whisper_model_name = target_model
            self.output(f"NEO > Local Whisper ({target_model}) ready.")
        except Exception as exc:
            self.whisper_model = None
            self.whisper_ready = False
            self.output(f"NEO > Whisper initialization failed: {exc}")

    # ============================================================
    # MICROPHONE DIAGNOSTICS & ENUMERATION
    # ============================================================

    @staticmethod
    def get_input_devices_detailed() -> List[Dict[str, Any]]:
        """
        Returns rich metadata for all valid audio input endpoints.
        Filters out pure render/speaker endpoints and tags virtual vs physical mics.
        """
        devices = []
        p = None
        try:
            import pyaudio
            p = pyaudio.PyAudio()

            default_idx = None
            try:
                def_info = p.get_default_input_device_info()
                default_idx = def_info.get("index")
            except Exception:
                pass

            for idx in range(p.get_device_count()):
                try:
                    info = p.get_device_info_by_index(idx)
                    max_in = info.get("maxInputChannels", 0)
                    if max_in <= 0:
                        continue

                    raw_name = info.get("name", f"Microphone {idx}")
                    api_idx = info.get("hostApi", 0)
                    try:
                        api_info = p.get_host_api_info_by_index(api_idx)
                        api_name = api_info.get("name", "")
                    except Exception:
                        api_name = ""

                    name_lower = raw_name.lower()
                    is_virtual = any(kw in name_lower for kw in VIRTUAL_DEVICE_KEYWORDS)
                    is_default = (idx == default_idx)
                    sample_rate = int(info.get("defaultSampleRate", 16000))

                    devices.append({
                        "index": idx,
                        "name": raw_name,
                        "channels": max_in,
                        "sample_rate": sample_rate,
                        "host_api": api_name,
                        "is_default": is_default,
                        "is_virtual": is_virtual,
                    })
                except Exception:
                    continue
        except Exception:
            pass
        finally:
            if p:
                try:
                    p.terminate()
                except Exception:
                    pass

        return devices

    @classmethod
    def get_available_microphones(cls) -> List[Tuple[int, str]]:
        """
        Returns indexed list of available audio input devices formatted with virtual/physical tags.
        Maintains backward compatibility with (index, display_name) signature.
        """
        detailed = cls.get_input_devices_detailed()
        if detailed:
            results = []
            for d in detailed:
                tag = "[Virtual]" if d["is_virtual"] else "[Physical]"
                def_tag = " (System Default)" if d["is_default"] else ""
                label = f"{d['name']} {tag} ({d['host_api']}){def_tag}"
                results.append((d["index"], label))
            return results

        # Fallback to standard speech_recognition enumeration if PyAudio inspection fails
        try:
            names = sr.Microphone.list_microphone_names()
            return [(idx, name) for idx, name in enumerate(names)]
        except Exception:
            return []

    @classmethod
    def resolve_input_device(cls) -> Tuple[Optional[int], str, bool]:
        """
        Deterministically resolves the optimal audio input device:
        1. Checks saved mic_device_index and mic_device_name.
        2. Validates index resilience (matches by name if index shifted).
        3. If unconfigured or pointing to silent virtual driver (e.g. AudioRelay / Cable),
           automatically falls back to the first available physical microphone.
        Returns: (resolved_index, device_name, is_virtual)
        """
        detailed = cls.get_input_devices_detailed()
        if not detailed:
            # Fallback if enumeration is empty
            cfg_idx = settings.get("mic_device_index", MICROPHONE_INDEX)
            return (cfg_idx, f"Device {cfg_idx}" if cfg_idx is not None else "System Default", False)

        devices_by_idx = {d["index"]: d for d in detailed}
        cfg_idx = settings.get("mic_device_index")
        cfg_name = settings.get("mic_device_name", "")

        # 1. Check if user configured a valid device
        if cfg_idx is not None and cfg_idx in devices_by_idx:
            dev = devices_by_idx[cfg_idx]
            # Verify name hasn't completely shifted to a completely different device
            if not cfg_name or cfg_name.lower() in dev["name"].lower() or dev["name"].lower() in cfg_name.lower():
                return (dev["index"], dev["name"], dev["is_virtual"])

        # 2. Resilient name match if index shifted (e.g. USB mic unplugged/replugged)
        if cfg_name:
            for d in detailed:
                if cfg_name.lower() in d["name"].lower() or d["name"].lower() in cfg_name.lower():
                    # Update new shifted index
                    settings.set("mic_device_index", d["index"])
                    return (d["index"], d["name"], d["is_virtual"])

        # 3. If unconfigured or default is a virtual driver, route to physical microphone
        default_dev = next((d for d in detailed if d["is_default"]), detailed[0])
        physical_dev = next((d for d in detailed if not d["is_virtual"]), None)

        if default_dev["is_virtual"] and physical_dev is not None:
            # Auto-route away from silent virtual device to physical hardware microphone
            settings.set("mic_device_index", physical_dev["index"])
            settings.set("mic_device_name", physical_dev["name"])
            try:
                settings.save()
            except Exception:
                pass
            return (physical_dev["index"], physical_dev["name"], False)

        return (default_dev["index"], default_dev["name"], default_dev["is_virtual"])

    @classmethod
    def test_microphone_input(cls, device_index: Optional[int] = None, duration: float = 1.0) -> Dict[str, Any]:
        """
        Safely records an in-memory sample for `duration` seconds and reports audio energy.
        Computes RMS and Peak values. Does NOT save, write to disk, or log private recordings.
        """
        p = None
        stream = None
        try:
            import pyaudio
            p = pyaudio.PyAudio()

            if device_index is None:
                try:
                    def_info = p.get_default_input_device_info()
                    device_index = def_info.get("index")
                except Exception:
                    device_index = None

            if device_index is None:
                return {
                    "success": False,
                    "error": "No input device available.",
                    "device_index": None,
                    "device_name": "None",
                    "rms": 0.0,
                    "peak": 0,
                    "status": "error",
                    "status_description": "No input device detected."
                }

            dev_info = p.get_device_info_by_index(device_index)
            dev_name = dev_info.get("name", f"Device {device_index}")
            sample_rate = int(dev_info.get("defaultSampleRate", 16000))
            if sample_rate <= 0 or sample_rate > 96000:
                sample_rate = 16000

            # Try 16000Hz first (standard Whisper rate), then device default
            rates_to_try = [16000, sample_rate, 44100, 48000]
            opened = False
            last_err = None
            for rate in rates_to_try:
                try:
                    stream = p.open(
                        format=pyaudio.paInt16,
                        channels=1,
                        rate=rate,
                        input=True,
                        input_device_index=device_index,
                        frames_per_buffer=1024
                    )
                    sample_rate = rate
                    opened = True
                    break
                except Exception as e:
                    last_err = e

            if not opened or stream is None:
                return {
                    "success": False,
                    "error": f"Failed to open device: {last_err}",
                    "device_index": device_index,
                    "device_name": dev_name,
                    "rms": 0.0,
                    "peak": 0,
                    "status": "error",
                    "status_description": f"Device open failed ({last_err})"
                }

            # Read frames in memory
            num_frames = max(1, min(int(sample_rate / 1024 * duration), 60))
            chunks = []
            for _ in range(num_frames):
                data = stream.read(1024, exception_on_overflow=False)
                chunks.append(data)

            stream.stop_stream()
            stream.close()
            stream = None

            raw = b"".join(chunks)
            samples = np.frombuffer(raw, dtype=np.int16)
            if len(samples) > 0:
                rms = float(np.sqrt(np.mean(samples.astype(np.float64)**2)))
                peak = int(np.max(np.abs(samples)))
            else:
                rms = 0.0
                peak = 0

            # Distinguish silent / disconnected vs ambient / active speech
            if rms < 5.0:
                status = "silent"
                status_desc = "Zero audio energy detected. Device is silent, muted, or an inactive virtual driver."
            elif rms < 100.0:
                status = "low_energy"
                status_desc = "Low energy detected. Device is receiving quiet background noise or faint speech."
            else:
                status = "active"
                status_desc = "Clear audio signal detected. Microphone input is active and operational."

            return {
                "success": True,
                "device_index": device_index,
                "device_name": dev_name,
                "sample_rate": sample_rate,
                "rms": round(rms, 1),
                "peak": peak,
                "status": status,
                "status_description": status_desc
            }

        except Exception as exc:
            return {
                "success": False,
                "error": str(exc),
                "device_index": device_index,
                "device_name": f"Device {device_index}",
                "rms": 0.0,
                "peak": 0,
                "status": "error",
                "status_description": f"Microphone check error: {exc}"
            }
        finally:
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            if p:
                try:
                    p.terminate()
                except Exception:
                    pass

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

        # Resolve best available device (resilient to index shifts and virtual silent devices)
        device_index, device_name, is_virtual = self.resolve_input_device()

        if is_virtual:
            self.output(f"NEO > [WARNING] Active input device is a virtual driver ('{device_name}'). "
                        f"If no speech is captured, select a physical microphone in Settings.")

        try:
            with sr.Microphone(device_index=device_index) as source:
                self.output(f"NEO > ● LISTENING ([{device_index}] {device_name})")

                # Ambient noise calibration with reasonable duration and clamped bounds
                ambient_dur = float(settings.get("mic_ambient_duration", 0.4))
                try:
                    self.recognizer.adjust_for_ambient_noise(source, duration=ambient_dur)
                    # Protect against extreme values
                    self.recognizer.energy_threshold = max(
                        150.0,
                        min(float(self.recognizer.energy_threshold), 2500.0)
                    )
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

            if text is None or not text.strip():
                # Clearly distinguish empty transcript from capture timeout
                self.output("NEO > Speech captured, but no discernible words were recognized.")
                self.state("READY")
                return None

            self.output(f"YOU > {text}")
            return text

        except sr.WaitTimeoutError:
            self.output("NEO > No speech detected within 8s. (Tip: Speak closer to your microphone or check microphone selection in Settings).")
        except OSError as exc:
            self.state("ERROR")
            self.output(f"NEO > [ERROR] Could not open microphone [{device_index}] '{device_name}': {exc}. "
                        f"Check Windows microphone privacy permissions and device selection in Settings.")
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