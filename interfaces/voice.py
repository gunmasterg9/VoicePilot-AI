"""
NEO AI - Voice Interface Pipeline
Coordinates audio capture, speech recognition, assistant execution,
and natural text-to-speech with automatic offline fallback.
"""

import os
import time
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

# Ensure SpeechRecognition Microphone context manager does not raise AttributeError on uninitialized streams (e.g. Device 17)
try:
    _orig_mic_exit = sr.Microphone.__exit__

    def _safe_mic_exit(self, exc_type, exc_value, traceback):
        if getattr(self, "stream", None) is not None:
            try:
                self.stream.close()
            except Exception:
                pass
        self.stream = None
        if getattr(self, "audio", None) is not None:
            try:
                self.audio.terminate()
            except Exception:
                pass

    sr.Microphone.__exit__ = _safe_mic_exit

    _orig_mic_enter = sr.Microphone.__enter__

    def _safe_mic_enter(self):
        res = _orig_mic_enter(self)
        if getattr(self, "stream", None) is None:
            raise OSError(f"Failed to open audio input stream on microphone device [{self.device_index}]")
        return res

    sr.Microphone.__enter__ = _safe_mic_enter
except Exception:
    pass

from config import MICROPHONE_INDEX
from core.settings import settings
import re
from interfaces.tts import TTSManager

# Module-level cache for Faster-Whisper models to prevent redundant reloads across worker runs
_GLOBAL_WHISPER_CACHE: Dict[str, WhisperModel] = {}

VIRTUAL_DEVICE_KEYWORDS = [
    "virtual", "cable", "stereomix", "stereo mix", "audiorelay", "streamer", "mapper"
]


def validate_transcription(
    text: Optional[str],
    language: Optional[str] = "en",
    quality: Optional[Dict[str, Any]] = None
) -> Tuple[bool, str, str]:
    """
    Validates recognized text before sending to the command router or agent.
    Filters empty inputs, extreme noise/hallucination metrics, repetitive loops,
    and isolated ambiguous fragments (e.g. 'ndo', 'kaakwar').
    Returns: (is_valid, cleaned_text, reason_or_message)
    """
    if not text:
        return False, "", "empty_audio"

    # 1. Normalize whitespace and harmless edge punctuation
    cleaned = re.sub(r"\s+", " ", str(text)).strip(" .,!?;:\"'~`_-")
    if not cleaned:
        return False, "", "empty_after_normalization"

    # 2. Check Whisper quality metrics if provided
    if quality:
        if quality.get("empty", False):
            return False, cleaned, "empty_audio"
        if quality.get("silent", False):
            return False, cleaned, "silent_audio"
        no_speech = quality.get("no_speech_prob", 0.0)
        avg_logprob = quality.get("avg_logprob", 0.0)
        compression_ratio = quality.get("compression_ratio", 1.0)

        if no_speech > 0.65:
            return False, cleaned, f"high_no_speech_prob ({no_speech:.2f})"
        if avg_logprob < -1.8:
            return False, cleaned, f"low_logprob ({avg_logprob:.2f})"
        if compression_ratio > 2.4:
            return False, cleaned, f"hallucinatory_repetition (compression_ratio={compression_ratio:.2f})"

    # 3. Check for known hallucination patterns common in Whisper models on noise
    lower = cleaned.lower()
    hallucination_phrases = {
        "subtitles by", "amara.org", "thank you for watching", "thanks for watching",
        "please subscribe", "subscribe to my channel", "mbc", "captioned by",
        "you you you", "thank you thank you", "the end."
    }
    if any(h in lower for h in hallucination_phrases):
        return False, cleaned, "known_hallucination_pattern"

    # 4. Check for ambiguous noise fragments using router
    try:
        from core.router import is_ambiguous_fragment
        if is_ambiguous_fragment(cleaned):
            return False, cleaned, f"ambiguous_fragment ('{cleaned}')"
    except Exception:
        pass

    return True, cleaned, "ok"


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

        # Quality & cancellation tracking
        self._last_transcription_quality: Dict[str, Any] = {}
        self._cancelled: bool = False

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

    _DETAILED_DEVICES_CACHE: Optional[List[Dict[str, Any]]] = None
    _DETAILED_CACHE_TIME: float = 0.0

    @classmethod
    def get_input_devices_detailed(cls, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Returns rich metadata for all valid audio input endpoints.
        Filters out pure render/speaker endpoints and tags virtual vs physical mics.
        """
        now = time.monotonic()
        if not force_refresh and cls._DETAILED_DEVICES_CACHE is not None and (now - cls._DETAILED_CACHE_TIME < 5.0):
            return cls._DETAILED_DEVICES_CACHE

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

        cls._DETAILED_DEVICES_CACHE = devices
        cls._DETAILED_CACHE_TIME = now
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

    def _get_uncertainty_message(self, lang_setting: Optional[str] = None) -> str:
        """Returns language-appropriate clarification request."""
        lang = lang_setting or settings.get("speech_language", "en")
        if lang == "hi":
            return "मुझे समझ नहीं आया। कृपया दोबारा बोलें।"
        elif lang == "gu":
            return "મને સમજાયું નથી. કૃપા કરીને ફરી પ્રયાસ કરો."
        return "I didn't understand. Please try again."

    def cancel(self):
        """Cancels any ongoing recording, transcription, or speech."""
        self._cancelled = True
        self.stop_speaking()
        if hasattr(self.agent, "cancel_current_operation"):
            self.agent.cancel_current_operation()

    # ============================================================
    # AUDIO -> TEMP WAV (FORCED 16KHZ MONO)
    # ============================================================

    def _audio_to_wav(self, audio: sr.AudioData) -> str:
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_path = temp_file.name
        temp_file.close()

        try:
            # Force 16000Hz 16-bit mono PCM conversion for Whisper compatibility
            try:
                wav_data = audio.get_wav_data(convert_rate=16000, convert_width=2)
            except Exception:
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
    # WHISPER TRANSCRIPTION WITH QUALITY SIGNALS
    # ============================================================

    def _transcribe(self, wav_path: str) -> Optional[str]:
        if not self.whisper_ready or self.whisper_model is None:
            return None

        self._last_transcription_quality = {}

        try:
            orig_sr = 16000
            audio_input = wav_path
            try:
                import soundfile as sf
                data, read_sr = sf.read(wav_path, dtype="float32")
                orig_sr = read_sr
                # Downmix multi-channel to mono
                if data.ndim > 1:
                    data = np.mean(data, axis=1)
                # Resample to 16000Hz if device captured at different rate (e.g. 44.1kHz, 48kHz)
                if read_sr != 16000 and len(data) > 0:
                    target_len = int(len(data) * 16000 / read_sr)
                    data = np.interp(
                        np.linspace(0, len(data), target_len, endpoint=False),
                        np.arange(len(data)),
                        data
                    ).astype(np.float32)
                audio_input = data
            except Exception:
                audio_input = wav_path

            # Diagnostic audio energy check
            duration = 0.0
            rms = 0.0
            peak = 0.0
            if isinstance(audio_input, np.ndarray):
                duration = len(audio_input) / 16000.0
                rms = float(np.sqrt(np.mean(audio_input.astype(np.float64)**2))) if len(audio_input) > 0 else 0.0
                peak = float(np.max(np.abs(audio_input))) if len(audio_input) > 0 else 0.0

                self.output(
                    f"NEO > [ASR] Audio metrics: duration={duration:.1f}s, sample_rate=16000Hz "
                    f"(source: {orig_sr}Hz), channels=1, rms={rms:.4f}, peak={peak:.4f}"
                )

                if duration < 0.2:
                    self.output("NEO > [ASR] Captured audio is empty.")
                    self._last_transcription_quality = {"empty": True, "duration": duration}
                    return ""

                # Silence gate: prevent Whisper from hallucinating words on silent audio
                if rms < 0.002 or peak < 0.008:
                    self.output(
                        f"NEO > [ASR] Captured audio is silent (rms={rms:.4f}, peak={peak:.4f}). "
                        "Skipping Whisper to prevent hallucinations."
                    )
                    self._last_transcription_quality = {
                        "silent": True, "rms": rms, "peak": peak, "duration": duration
                    }
                    return ""

            # Language selection from settings
            lang_setting = settings.get("speech_language", "en")
            if lang_setting in {"auto", None, ""}:
                language = None
                self.output(f"NEO > [ASR] Language mode: AUTO (detecting), Model: {self._current_whisper_model_name}")
            else:
                language = lang_setting
                self.output(f"NEO > [ASR] Language mode: {language.upper()} (configured), Model: {self._current_whisper_model_name}")

            # Multilingual model auto-selection if needed
            if lang_setting in {"hi", "gu", "auto"} and self._current_whisper_model_name and self._current_whisper_model_name.endswith(".en"):
                self._load_whisper_model("tiny")

            try:
                segments, info = self.whisper_model.transcribe(
                    audio_input,
                    language=language,
                    beam_size=1,
                    best_of=1,
                    temperature=0,
                    vad_filter=True,
                    condition_on_previous_text=False
                )
            except Exception:
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
            if language is None and detected_lang:
                self.output(f"NEO > [ASR] Auto-detected language: {detected_lang.upper()} ({prob:.0%})")

            # Collect segments and filter out noise
            seg_list = list(segments)
            valid_segments = []
            for seg in seg_list:
                no_speech = getattr(seg, "no_speech_prob", 0.0)
                comp_ratio = getattr(seg, "compression_ratio", 1.0)
                avg_logprob = getattr(seg, "avg_logprob", 0.0)

                if no_speech > 0.70 or comp_ratio > 2.4 or avg_logprob < -1.8:
                    continue
                if seg.text.strip():
                    valid_segments.append(seg)

            raw_text = " ".join(s.text.strip() for s in valid_segments).strip()

            quality_signals = {
                "avg_logprob": float(np.mean([s.avg_logprob for s in valid_segments])) if valid_segments else -999.0,
                "no_speech_prob": float(np.mean([s.no_speech_prob for s in valid_segments])) if valid_segments else 1.0,
                "compression_ratio": float(np.mean([s.compression_ratio for s in valid_segments])) if valid_segments else 1.0,
                "duration": duration,
                "rms": rms,
                "peak": peak,
                "language": detected_lang or language or "en"
            }
            self._last_transcription_quality = quality_signals

            if raw_text:
                self.output(
                    f"NEO > [ASR] Whisper result: '{raw_text}' "
                    f"(avg_logprob={quality_signals['avg_logprob']:.2f}, no_speech={quality_signals['no_speech_prob']:.2f})"
                )

            return raw_text

        except Exception as exc:
            self.output(f"NEO > Whisper error: {exc}")
            return None

    # ============================================================
    # LISTEN WITH CANCELLATION & TRANSCRIPTION VALIDATION
    # ============================================================

    def listen_once(self) -> Optional[str]:
        self.state("LISTENING")
        wav_path = None
        self._cancelled = False

        if getattr(self.agent, "is_cancelled", False) is True:
            self.state("IDLE")
            return None

        # Resolve best available device (resilient to index shifts and virtual silent devices)
        device_index, device_name, is_virtual = self.resolve_input_device()

        if is_virtual:
            self.output(f"NEO > [WARNING] Active input device is a virtual driver ('{device_name}'). "
                        f"If no speech is captured, select a physical microphone in Settings.")

        try:
            with sr.Microphone(device_index=device_index) as source:
                self.output(f"NEO > ● LISTENING ([{device_index}] {device_name})")

                # Ambient noise calibration: only run full calibration on initial capture or if threshold is uncalibrated
                if not getattr(self, "_is_calibrated", False):
                    ambient_dur = float(settings.get("mic_ambient_duration", 0.3))
                    try:
                        self.recognizer.adjust_for_ambient_noise(source, duration=ambient_dur)
                        self.recognizer.energy_threshold = max(
                            150.0,
                            min(float(self.recognizer.energy_threshold), 2500.0)
                        )
                        self._is_calibrated = True
                    except Exception:
                        pass

                calibrated_threshold = float(self.recognizer.energy_threshold)
                self.output(
                    f"NEO > Microphone ready. Calibrated speech threshold: "
                    f"{calibrated_threshold:.0f}. Speak now..."
                )

                if self._cancelled or getattr(self.agent, "is_cancelled", False) is True:
                    self.state("IDLE")
                    return None

                original_dynamic_threshold = self.recognizer.dynamic_energy_threshold
                audio = None
                try:
                    for attempt in range(2):
                        if self._cancelled or getattr(self.agent, "is_cancelled", False) is True:
                            break
                        try:
                            audio = self.recognizer.listen(
                                source,
                                timeout=8,
                                phrase_time_limit=20
                            )
                            if attempt:
                                self.output("NEO > Speech captured on the sensitivity retry.")
                            break
                        except sr.WaitTimeoutError:
                            if attempt == 1:
                                raise

                            current_threshold = float(self.recognizer.energy_threshold)
                            retry_threshold = max(
                                80.0,
                                min(current_threshold * 0.55, 250.0)
                            )
                            self.recognizer.energy_threshold = retry_threshold
                            self.recognizer.dynamic_energy_threshold = False
                            self.output(
                                "NEO > No speech trigger detected yet. Retrying once "
                                f"with increased microphone sensitivity "
                                f"(threshold {retry_threshold:.0f}). Speak clearly now..."
                            )
                finally:
                    self.recognizer.dynamic_energy_threshold = original_dynamic_threshold
                    self.recognizer.energy_threshold = calibrated_threshold

            if self._cancelled or getattr(self.agent, "is_cancelled", False) is True:
                self.state("IDLE")
                return None

            if audio is None:
                self.state("IDLE")
                return None

            self.output("NEO > Speech captured.")
            self.state("TRANSCRIBING")
            self.output("NEO > Transcribing locally...")

            t_asr_start = time.perf_counter()
            wav_path = self._audio_to_wav(audio)
            text = self._transcribe(wav_path)
            asr_latency = time.perf_counter() - t_asr_start
            self._last_recognition_latency = asr_latency
            self.output(f"NEO > [LATENCY] Speech recognition: {asr_latency:.2f}s")

            if text is None or not str(text).strip():
                # Clearly distinguish empty transcript from capture timeout
                self.output("NEO > Speech captured, but no discernible words were recognized.")
                self.state("IDLE")
                return None

            # Transcription validation layer
            lang_setting = settings.get("speech_language", "en")
            is_valid, cleaned_text, reason = validate_transcription(
                text, language=lang_setting, quality=self._last_transcription_quality
            )

            if not is_valid:
                self.output(f"NEO > [ASR] Transcription rejected: {reason}")
                uncertainty_msg = self._get_uncertainty_message(lang_setting)
                self.output(f"NEO > {uncertainty_msg}")
                self.state("IDLE")
                return None

            self.output(f"YOU > {cleaned_text}")
            self.state("ROUTING")
            return cleaned_text

        except sr.WaitTimeoutError:
            self.output(
                "NEO > No speech detected after two listening attempts. "
                "The microphone may be active but the speech signal may be too quiet "
                "for detection. Check the selected input device and Windows input level "
                "in Settings, then try speaking closer to the microphone."
            )
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

        self.state("IDLE")
        return None

    # ============================================================
    # PROCESS COMMAND
    # ============================================================

    def process_voice_command(self) -> Optional[str]:
        command = self.listen_once()
        if not command:
            self.state("IDLE")
            return None

        try:
            from core.router import route_direct_command, CommandRouter, Intent
            router = CommandRouter()
            intent, details = router.classify_intent(command)

            if intent == Intent.SYSTEM_CONTROL:
                self.state("EXECUTING")
                self.output("NEO > [ROUTER] Intent: SYSTEM_CONTROL (stop/cancel)")
            elif intent == Intent.PC_COMMAND:
                self.state("EXECUTING")
                tool = details.get("tool", "local_handler")
                self.output(f"NEO > [ROUTER] Intent: PC_COMMAND (Handler: {tool})")
            elif intent == Intent.DESTRUCTIVE_ACTION:
                self.state("EXECUTING")
                self.output(f"NEO > [ROUTER] Intent: DESTRUCTIVE_ACTION ({details.get('tool')})")
            elif intent == Intent.AMBIGUOUS:
                self.state("IDLE")
                self.output("NEO > [ROUTER] Intent: AMBIGUOUS (Input rejected)")
                uncertainty_msg = self._get_uncertainty_message()
                self.output(f"NEO > {uncertainty_msg}")
                self.speak(uncertainty_msg)
                return uncertainty_msg
            else:
                self.state("THINKING")
                self.output("NEO > [ROUTER] Intent: CONVERSATIONAL (Routing to local Ollama)")

            t_exec_start = time.perf_counter()
            response = self.agent.run(command)
            exec_latency = time.perf_counter() - t_exec_start
            self._last_execution_latency = exec_latency
            self.output(f"NEO > [LATENCY] Command execution: {exec_latency:.3f}s")

            if response is None:
                response = "Command completed."

            summary = str(response).split("\n")[0][:80]
            self.output(f"NEO > [ACTION RESULT] {summary}")

            # Concise offline TTS confirmation
            tts_text = str(response).split("\n")[0].strip()
            if len(tts_text) > 120:
                tts_text = tts_text[:117] + "..."
            self.speak(tts_text)
            self.state("IDLE")
            return response

        except Exception as exc:
            self.state("ERROR")
            self.output(f"NEO > Agent error: {exc}")
            self.state("IDLE")
            return None