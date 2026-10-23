"""
NEO AI - Text-to-Speech (TTS) Architecture
Provides interchangeable Online Neural (edge-tts) and Offline SAPI (pyttsx3)
TTS providers with automatic fallback, cancel/stop controls, and status reporting.
"""

import asyncio
import os
import tempfile
import threading
from abc import ABC, abstractmethod
from typing import Callable, Optional, List, Tuple, Dict

import sounddevice as sd
import soundfile as sf
import pyttsx3
import numpy as np

from core.settings import settings


# Supported Online Neural Voices (edge-tts) catalog by language
SUPPORTED_NEURAL_VOICES = {
    "en": [
        ("English - Aria (Natural Female)", "en-US-AriaNeural"),
        ("English - Guy (Natural Male)", "en-US-GuyNeural"),
    ],
    "hi": [
        ("Hindi - Swara (Natural Female)", "hi-IN-SwaraNeural"),
        ("Hindi - Madhur (Natural Male)", "hi-IN-MadhurNeural"),
    ],
    "gu": [
        ("Gujarati - Dhwani (Natural Female)", "gu-IN-DhwaniNeural"),
        ("Gujarati - Niranjan (Natural Male)", "gu-IN-NiranjanNeural"),
    ]
}

ALL_NEURAL_VOICE_NAMES = {
    voice_name
    for voice_list in SUPPORTED_NEURAL_VOICES.values()
    for _, voice_name in voice_list
}

# Backward-compatibility alias
NEURAL_VOICES = {
    "en": "en-US-AriaNeural",
    "en_male": "en-US-GuyNeural",
    "hi": "hi-IN-SwaraNeural",
    "hi_male": "hi-IN-MadhurNeural",
    "gu": "gu-IN-DhwaniNeural",
    "gu_male": "gu-IN-NiranjanNeural",
}


class BaseTTSProvider(ABC):
    """Abstract base class for all TTS providers."""

    @abstractmethod
    def speak(self, text: str, on_start: Optional[Callable] = None, on_done: Optional[Callable] = None) -> bool:
        """Synthesize and play speech. Returns True if successful, False otherwise."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Immediately interrupt and stop audio playback."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is operational."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass


class OnlineNeuralTTSProvider(BaseTTSProvider):
    """
    Online Natural Neural TTS Provider using Microsoft Edge Neural Voices.
    High-fidelity, natural sounding voice with no API key requirement.
    Supports English, Hindi, Gujarati with rate, volume, and device routing.
    """

    def __init__(
        self,
        voice: Optional[str] = None,
        rate: int = 180,
        volume: float = 1.0,
        output_device: Optional[int] = None
    ):
        self._voice = voice or settings.get("tts_voice_online", "en-US-AriaNeural")
        self._rate = rate
        self._volume = volume
        self._output_device = output_device if output_device is not None else settings.get("tts_output_device_index")
        self._is_playing = False
        self._stop_event = threading.Event()

    @property
    def provider_name(self) -> str:
        return f"Online Neural ({self._voice})"

    def is_available(self) -> bool:
        try:
            import edge_tts
            return True
        except ImportError:
            return False

    def set_voice(self, voice_name: str):
        if not voice_name or not voice_name.strip():
            raise ValueError("Voice name cannot be empty.")
        if voice_name not in ALL_NEURAL_VOICE_NAMES:
            raise ValueError(f"Requested voice '{voice_name}' is not in the verified Edge Neural voice catalog.")
        self._voice = voice_name

    def set_output_device(self, device_index: Optional[int]):
        self._output_device = device_index

    def set_volume(self, volume: float):
        self._volume = max(0.0, min(1.0, float(volume)))

    def set_rate(self, rate: int):
        self._rate = int(rate)

    def stop(self) -> None:
        self._stop_event.set()
        try:
            sd.stop()
        except Exception:
            pass
        self._is_playing = False

    def speak(self, text: str, on_start: Optional[Callable] = None, on_done: Optional[Callable] = None) -> bool:
        if not text or not text.strip():
            return False

        self._stop_event.clear()
        temp_mp3 = None

        try:
            import edge_tts

            # Calculate rate offset relative to 180 wpm
            rate_pct = int(((self._rate - 180) / 180) * 100)
            rate_str = f"{rate_pct:+d}%"

            async def _synthesize():
                communicate = edge_tts.Communicate(text.strip(), self._voice, rate=rate_str)
                fd, path = tempfile.mkstemp(suffix=".mp3")
                os.close(fd)
                await communicate.save(path)
                return path

            # Synthesize audio with 8 second timeout to detect network issues quickly
            temp_mp3 = asyncio.run(asyncio.wait_for(_synthesize(), timeout=8.0))

            if self._stop_event.is_set():
                return False

            if not temp_mp3 or not os.path.exists(temp_mp3) or os.path.getsize(temp_mp3) < 100:
                return False

            # Decode audio using soundfile and play via sounddevice
            data, samplerate = sf.read(temp_mp3, dtype="float32")

            # Scale volume cleanly
            if self._volume != 1.0:
                data = np.clip(data * self._volume, -1.0, 1.0)

            if self._stop_event.is_set():
                return False

            if on_start:
                on_start()

            self._is_playing = True
            sd.play(data, samplerate, device=self._output_device)

            # Wait for completion or stop signal
            while sd.get_stream().active:
                if self._stop_event.is_set():
                    sd.stop()
                    break
                sd.sleep(50)

            self._is_playing = False
            if on_done and not self._stop_event.is_set():
                on_done()

            return not self._stop_event.is_set()

        except Exception as exc:
            # Let caller know online synthesis failed so it can trigger fallback
            self._is_playing = False
            raise RuntimeError(f"Online Neural TTS failed: {exc}") from exc

        finally:
            if temp_mp3 and os.path.exists(temp_mp3):
                try:
                    os.remove(temp_mp3)
                except Exception:
                    pass


class OfflineSapiTTSProvider(BaseTTSProvider):
    """
    Offline Text-to-Speech Provider using Windows SAPI5 via pyttsx3.
    Always available offline without internet access.
    """

    def __init__(self, voice_index: int = 0, rate: int = 180, volume: float = 1.0):
        self._rate = rate
        self._volume = volume
        self._voice_index = voice_index
        self._engine = None
        self._lock = threading.Lock()
        self._init_engine()

    def _init_engine(self):
        try:
            try:
                import pythoncom
                pythoncom.CoInitialize()
            except Exception:
                pass

            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", self._rate)
            self._engine.setProperty("volume", self._volume)

            voices = self._engine.getProperty("voices")
            if voices and 0 <= self._voice_index < len(voices):
                self._engine.setProperty("voice", voices[self._voice_index].id)
        except Exception:
            self._engine = None

    def set_rate(self, rate: int):
        self._rate = int(rate)
        if self._engine:
            try:
                self._engine.setProperty("rate", self._rate)
            except Exception:
                pass

    def set_volume(self, volume: float):
        self._volume = max(0.0, min(1.0, float(volume)))
        if self._engine:
            try:
                self._engine.setProperty("volume", self._volume)
            except Exception:
                pass

    def provider_name(self) -> str:
        return "Offline SAPI5 (Windows Local)"

    def is_available(self) -> bool:
        return self._engine is not None

    def stop(self) -> None:
        try:
            if self._engine:
                self._engine.stop()
        except Exception:
            pass

    def speak(self, text: str, on_start: Optional[Callable] = None, on_done: Optional[Callable] = None) -> bool:
        if not text or not text.strip():
            return False

        with self._lock:
            try:
                try:
                    import pythoncom
                    pythoncom.CoInitialize()
                except Exception:
                    pass

                if not self._engine:
                    self._init_engine()

                if not self._engine:
                    return False

                if on_start:
                    on_start()

                self._engine.say(str(text))
                self._engine.runAndWait()

                if on_done:
                    on_done()

                return True
            except Exception as exc:
                print(f"[ERROR] Offline SAPI TTS failed: {exc}")
                return False


class TTSManager:
    """
    Unified TTS Manager that coordinates Online Neural and Offline Fallback TTS.
    Prevents overlapping speech, supports instant cancellation, and reports active provider.
    """

    def __init__(self, log_callback: Optional[Callable[[str], None]] = None):
        self.log = log_callback or print
        self.offline_provider = OfflineSapiTTSProvider(
            voice_index=settings.get("tts_voice_offline_index", 0),
            rate=settings.get("tts_speech_rate", 180),
            volume=settings.get("tts_volume", 1.0)
        )
        self.online_provider = OnlineNeuralTTSProvider(
            voice=settings.get("tts_voice_online", "en-US-AriaNeural"),
            rate=settings.get("tts_speech_rate", 180),
            volume=settings.get("tts_volume", 1.0),
            output_device=settings.get("tts_output_device_index")
        )
        self._current_provider_name = "Offline SAPI5"
        self._is_speaking = False
        self._lock = threading.Lock()

    @staticmethod
    def get_available_output_devices() -> List[Tuple[int, str]]:
        devices = []
        try:
            for idx, dev in enumerate(sd.query_devices()):
                if dev.get("max_output_channels", 0) > 0:
                    api = sd.query_hostapis(dev["hostapi"])["name"]
                    devices.append((idx, f"[{idx}] {dev['name']} ({api})"))
        except Exception:
            pass
        return devices

    def set_online_voice(self, voice_name: str):
        self.online_provider.set_voice(voice_name)

    def set_output_device(self, device_index: Optional[int]):
        self.online_provider.set_output_device(device_index)

    def set_volume(self, volume: float):
        self.online_provider.set_volume(volume)
        self.offline_provider.set_volume(volume)

    def set_rate(self, rate: int):
        self.online_provider.set_rate(rate)
        self.offline_provider.set_rate(rate)

    def get_active_provider_name(self) -> str:
        pref = settings.get("tts_provider", "online")
        if pref == "online" and self.online_provider.is_available():
            return self.online_provider.provider_name
        return self.offline_provider.provider_name

    def stop(self) -> None:
        """Immediately stop all audio playback from any provider."""
        self._is_speaking = False
        self.online_provider.stop()
        self.offline_provider.stop()

    def speak(
        self,
        text: str,
        on_start: Optional[Callable] = None,
        on_done: Optional[Callable] = None
    ) -> bool:
        """
        Synthesize speech using configured provider with automatic offline fallback.
        """
        if not text or not text.strip():
            return False

        with self._lock:
            # Stop any ongoing playback before starting new speech
            self.stop()
            self._is_speaking = True

            pref = settings.get("tts_provider", "online").lower()

            # 1. Try Online Neural TTS if selected
            if pref == "online" and self.online_provider.is_available():
                try:
                    self._current_provider_name = self.online_provider.provider_name
                    success = self.online_provider.speak(text, on_start=on_start, on_done=on_done)
                    if success:
                        self._is_speaking = False
                        return True
                    else:
                        self.log("NEO > [TTS FALLBACK] Online voice unavailable. Switching to offline SAPI fallback.")
                except Exception as exc:
                    self.log(f"NEO > [TTS FALLBACK] Online voice failed ({exc}). Switching to offline SAPI fallback.")

            # 2. Offline Fallback (or if configured as offline)
            self._current_provider_name = self.offline_provider.provider_name
            success = self.offline_provider.speak(text, on_start=on_start, on_done=on_done)
            self._is_speaking = False
            return success

    def is_speaking(self) -> bool:
        return self._is_speaking

    def get_status(self) -> dict:
        active_name = self.get_active_provider_name()
        return {
            "provider": active_name,
            "online_available": self.online_provider.is_available(),
            "offline_available": self.offline_provider.is_available(),
            "available": True,
            "is_speaking": self._is_speaking
        }


# Global singleton instance for app-wide use
tts_manager = TTSManager()
