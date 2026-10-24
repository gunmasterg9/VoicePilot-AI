"""
NEO AI - Microphone Subsystem Tests
Validates device enumeration, virtual vs physical resolution, index shift resilience,
in-memory energy measurement, ambient calibration clamping, Faster-Whisper model caching,
and actionable capture error handling.
"""

import os
import unittest
from unittest.mock import MagicMock, patch
import numpy as np

import speech_recognition as sr
from interfaces.voice import VoiceInterface, _GLOBAL_WHISPER_CACHE
from core.settings import settings


class TestMicrophoneSubsystem(unittest.TestCase):
    """Deterministic and simulated tests for NEO AI voice capture subsystem."""

    def setUp(self):
        self.mock_agent = MagicMock()
        self.mock_agent.run.return_value = "Command executed successfully."
        self.logs = []
        self.states = []
        self._orig_mic_idx = settings.get("mic_device_index")
        self._orig_mic_name = settings.get("mic_device_name")

    def tearDown(self):
        settings.set("mic_device_index", self._orig_mic_idx)
        settings.set("mic_device_name", self._orig_mic_name)
        try:
            settings.save()
        except Exception:
            pass

    def _output_logger(self, msg: str):
        self.logs.append(msg)

    def _state_logger(self, state: str):
        self.states.append(state)

    # ------------------------------------------------------------
    # 1. Device Enumeration & Metadata
    # ------------------------------------------------------------
    def test_device_enumeration_detailed(self):
        """Validates that get_input_devices_detailed returns properly structured device info."""
        devices = VoiceInterface.get_input_devices_detailed()
        self.assertIsInstance(devices, list)
        if devices:
            first = devices[0]
            self.assertIn("index", first)
            self.assertIn("name", first)
            self.assertIn("channels", first)
            self.assertIn("sample_rate", first)
            self.assertIn("is_virtual", first)
            self.assertIn("is_default", first)
            self.assertIn("host_api", first)

    def test_available_microphones_backward_compatible(self):
        """Ensures get_available_microphones returns list of (index, label) tuples."""
        mics = VoiceInterface.get_available_microphones()
        self.assertIsInstance(mics, list)
        for item in mics:
            self.assertIsInstance(item, tuple)
            self.assertEqual(len(item), 2)
            self.assertIsInstance(item[0], int)
            self.assertIsInstance(item[1], str)

    # ------------------------------------------------------------
    # 2. Resilient Device Resolution
    # ------------------------------------------------------------
    @patch("interfaces.voice.VoiceInterface.get_input_devices_detailed")
    def test_resolve_input_device_with_explicit_setting(self, mock_detailed):
        """When user selects a specific valid device index, it must be honored."""
        mock_detailed.return_value = [
            {"index": 1, "name": "Virtual Mic", "is_virtual": True, "is_default": True},
            {"index": 2, "name": "Realtek Microphone Array", "is_virtual": False, "is_default": False},
        ]
        with patch.object(settings, "get", side_effect=lambda k, d=None: 2 if k == "mic_device_index" else ""):
            idx, name, is_virt = VoiceInterface.resolve_input_device()
            self.assertEqual(idx, 2)
            self.assertEqual(name, "Realtek Microphone Array")
            self.assertFalse(is_virt)

    @patch("interfaces.voice.VoiceInterface.get_input_devices_detailed")
    def test_resolve_input_device_auto_fallback_from_virtual(self, mock_detailed):
        """When unconfigured and system default is a silent virtual driver, auto-route to physical mic."""
        mock_detailed.return_value = [
            {"index": 1, "name": "Virtual Mic for AudioRelay", "is_virtual": True, "is_default": True},
            {"index": 2, "name": "Microphone Array (Realtek)", "is_virtual": False, "is_default": False},
        ]
        with patch.object(settings, "get", side_effect=lambda k, d=None: None if k == "mic_device_index" else ""):
            idx, name, is_virt = VoiceInterface.resolve_input_device()
            self.assertEqual(idx, 2)
            self.assertEqual(name, "Microphone Array (Realtek)")
            self.assertFalse(is_virt)

    @patch("interfaces.voice.VoiceInterface.get_input_devices_detailed")
    def test_resolve_input_device_name_resilience_on_index_shift(self, mock_detailed):
        """When device index shifts (e.g. from 2 to 5 after reconnect), match by saved name."""
        mock_detailed.return_value = [
            {"index": 1, "name": "Virtual Mic", "is_virtual": True, "is_default": True},
            {"index": 5, "name": "Microphone Array (Realtek Audio)", "is_virtual": False, "is_default": False},
        ]
        def fake_get(key, default=None):
            if key == "mic_device_index":
                return 2  # old index, no longer in detailed list
            if key == "mic_device_name":
                return "Microphone Array (Realtek Audio)"
            return default

        with patch.object(settings, "get", side_effect=fake_get):
            idx, name, is_virt = VoiceInterface.resolve_input_device()
            self.assertEqual(idx, 5)
            self.assertIn("Realtek", name)

    # ------------------------------------------------------------
    # 3. In-Memory Audio Energy Measurement
    # ------------------------------------------------------------
    @patch("pyaudio.PyAudio")
    def test_safe_mic_test_silence_detection(self, mock_pyaudio_cls):
        """Synthesized pure silence (RMS 0.0) must be categorized as 'silent'."""
        mock_pa = MagicMock()
        mock_pyaudio_cls.return_value = mock_pa
        mock_pa.get_device_info_by_index.return_value = {
            "name": "Virtual Silent Mic",
            "defaultSampleRate": 16000
        }
        mock_stream = MagicMock()
        # 1024 samples of int16 zeros
        silent_frame = np.zeros(1024, dtype=np.int16).tobytes()
        mock_stream.read.return_value = silent_frame
        mock_pa.open.return_value = mock_stream

        result = VoiceInterface.test_microphone_input(device_index=1, duration=0.2)
        self.assertTrue(result["success"])
        self.assertEqual(result["rms"], 0.0)
        self.assertEqual(result["peak"], 0)
        self.assertEqual(result["status"], "silent")
        self.assertIn("Zero audio energy", result["status_description"])

    @patch("pyaudio.PyAudio")
    def test_safe_mic_test_low_energy_detection(self, mock_pyaudio_cls):
        """Synthesized low amplitude signal (RMS ~30) must be categorized as 'low_energy'."""
        mock_pa = MagicMock()
        mock_pyaudio_cls.return_value = mock_pa
        mock_pa.get_device_info_by_index.return_value = {
            "name": "Faint Mic",
            "defaultSampleRate": 16000
        }
        mock_stream = MagicMock()
        # Low energy int16 values between -40 and +40
        faint_frame = (np.ones(1024, dtype=np.int16) * 35).tobytes()
        mock_stream.read.return_value = faint_frame
        mock_pa.open.return_value = mock_stream

        result = VoiceInterface.test_microphone_input(device_index=2, duration=0.2)
        self.assertTrue(result["success"])
        self.assertGreater(result["rms"], 5.0)
        self.assertLess(result["rms"], 100.0)
        self.assertEqual(result["status"], "low_energy")

    @patch("pyaudio.PyAudio")
    def test_safe_mic_test_active_speech_detection(self, mock_pyaudio_cls):
        """Synthesized speech signal (RMS > 500) must be categorized as 'active'."""
        mock_pa = MagicMock()
        mock_pyaudio_cls.return_value = mock_pa
        mock_pa.get_device_info_by_index.return_value = {
            "name": "Realtek Microphone",
            "defaultSampleRate": 16000
        }
        mock_stream = MagicMock()
        # Generate 16000Hz 440Hz sine wave with amplitude 5000
        t = np.linspace(0, 1024/16000, 1024, endpoint=False)
        sine_wave = (np.sin(2 * np.pi * 440 * t) * 5000).astype(np.int16).tobytes()
        mock_stream.read.return_value = sine_wave
        mock_pa.open.return_value = mock_stream

        result = VoiceInterface.test_microphone_input(device_index=2, duration=0.2)
        self.assertTrue(result["success"])
        self.assertGreater(result["rms"], 2000.0)
        self.assertEqual(result["status"], "active")

    # ------------------------------------------------------------
    # 4. Faster-Whisper Model Caching
    # ------------------------------------------------------------
    @patch("interfaces.voice.WhisperModel")
    def test_whisper_model_global_cache_prevents_repeated_reloads(self, mock_whisper_cls):
        """Verifies that Faster-Whisper model instances are reused from cache across calls."""
        mock_instance = MagicMock()
        mock_whisper_cls.return_value = mock_instance

        # Clear test entry in cache
        test_model_name = "test_tiny_cache"
        _GLOBAL_WHISPER_CACHE.pop(test_model_name, None)

        # First instance loads model
        voice1 = VoiceInterface(agent=self.mock_agent, output_callback=self._output_logger)
        voice1._load_whisper_model(test_model_name)
        self.assertIn(test_model_name, _GLOBAL_WHISPER_CACHE)
        initial_call_count = mock_whisper_cls.call_count

        # Second instance reuses cached model without calling WhisperModel constructor
        voice2 = VoiceInterface(agent=self.mock_agent, output_callback=self._output_logger)
        voice2._load_whisper_model(test_model_name)
        self.assertEqual(mock_whisper_cls.call_count, initial_call_count)
        self.assertIs(voice2.whisper_model, mock_instance)

    # ------------------------------------------------------------
    # 5. Capture Error Handling & Actionable Messages
    # ------------------------------------------------------------
    @patch("speech_recognition.Microphone")
    @patch("interfaces.voice.VoiceInterface.resolve_input_device")
    def test_listen_once_timeout_actionable_message(self, mock_resolve, mock_mic):
        """sr.WaitTimeoutError must produce actionable guidance and return None."""
        mock_resolve.return_value = (2, "Realtek Mic", False)
        mock_mic_ctx = MagicMock()
        mock_mic.return_value.__enter__.return_value = mock_mic_ctx

        voice = VoiceInterface(agent=self.mock_agent, output_callback=self._output_logger, state_callback=self._state_logger)
        # Force listen to time out
        voice.recognizer.listen = MagicMock(side_effect=sr.WaitTimeoutError("Timed out"))

        result = voice.listen_once()
        self.assertIsNone(result)
        self.assertTrue(any("No speech detected after two listening attempts" in log for log in self.logs))
        self.assertTrue(any("Speak closer" in log or "Settings" in log for log in self.logs))

    @patch("speech_recognition.Microphone")
    @patch("interfaces.voice.VoiceInterface.resolve_input_device")
    def test_listen_once_retries_with_more_sensitive_threshold(self, mock_resolve, mock_mic):
        """A timeout at the calibrated threshold gets one bounded sensitivity retry."""
        mock_resolve.return_value = (2, "Realtek Mic", False)
        mock_mic_ctx = MagicMock()
        mock_mic.return_value.__enter__.return_value = mock_mic_ctx

        voice = VoiceInterface(
            agent=self.mock_agent,
            output_callback=self._output_logger,
            state_callback=self._state_logger
        )
        voice.recognizer.adjust_for_ambient_noise = MagicMock()
        voice.recognizer.energy_threshold = 600
        voice.recognizer.listen = MagicMock(
            side_effect=[sr.WaitTimeoutError("first timeout"), MagicMock(name="captured_audio")]
        )
        voice._audio_to_wav = MagicMock(return_value="nonexistent-test-audio.wav")
        voice._transcribe = MagicMock(return_value="what time is it")

        result = voice.listen_once()

        self.assertEqual(result, "what time is it")
        self.assertEqual(voice.recognizer.listen.call_count, 2)
        self.assertTrue(any("increased microphone sensitivity" in log for log in self.logs))
        self.assertTrue(any("Speech captured on the sensitivity retry" in log for log in self.logs))
        self.assertEqual(voice.recognizer.energy_threshold, 600)
        self.assertTrue(voice.recognizer.dynamic_energy_threshold)

    @patch("speech_recognition.Microphone")
    @patch("interfaces.voice.VoiceInterface.resolve_input_device")
    def test_listen_once_empty_transcript_distinguished_from_timeout(self, mock_resolve, mock_mic):
        """When speech is captured but transcription is empty, distinguish from timeout."""
        mock_resolve.return_value = (2, "Realtek Mic", False)
        mock_mic_ctx = MagicMock()
        mock_mic.return_value.__enter__.return_value = mock_mic_ctx

        voice = VoiceInterface(agent=self.mock_agent, output_callback=self._output_logger, state_callback=self._state_logger)
        voice.recognizer.listen = MagicMock(return_value=MagicMock())
        voice._audio_to_wav = MagicMock(return_value="dummy.wav")
        voice._transcribe = MagicMock(return_value="")  # Empty transcription

        result = voice.listen_once()
        self.assertIsNone(result)
        self.assertTrue(any("Speech captured, but no discernible words were recognized" in log for log in self.logs))
        self.assertFalse(any("No speech detected after two listening attempts" in log for log in self.logs))

    @patch("speech_recognition.Microphone")
    @patch("interfaces.voice.VoiceInterface.resolve_input_device")
    def test_listen_once_device_open_failure_actionable_message(self, mock_resolve, mock_mic):
        """OSError when opening microphone must produce actionable privacy/connection message."""
        mock_resolve.return_value = (1, "Virtual Mic", True)
        mock_mic.return_value.__enter__.side_effect = OSError("[Errno -9999] Unanticipated host error")

        voice = VoiceInterface(agent=self.mock_agent, output_callback=self._output_logger, state_callback=self._state_logger)

        result = voice.listen_once()
        self.assertIsNone(result)
        self.assertTrue(any("[ERROR] Could not open microphone" in log for log in self.logs))
        self.assertTrue(any("privacy permissions" in log.lower() for log in self.logs))


class TestHardwareMicrophoneVerification(unittest.TestCase):
    """
    Live Hardware Tests.
    Executed ONLY on Windows environments where a physical microphone is present.
    """

    def test_live_physical_microphone_audio_energy(self):
        """Checks actual physical microphone energy on the host machine without saving private audio."""
        detailed = VoiceInterface.get_input_devices_detailed()
        physical_devices = [d for d in detailed if not d["is_virtual"]]
        if not physical_devices:
            self.skipTest("No physical microphone available on this host environment.")

        # Test the first available physical microphone
        target_mic = physical_devices[0]
        result = VoiceInterface.test_microphone_input(device_index=target_mic["index"], duration=0.8)

        self.assertTrue(result["success"], f"Failed to read from hardware mic: {result.get('error')}")
        self.assertIn(result["status"], ["active", "low_energy", "silent"])
        print(f"\n[Hardware Telemetry] Physical Mic [{result['device_index']}] '{result['device_name']}': "
              f"RMS={result['rms']}, Peak={result['peak']}, Status={result['status']}")


if __name__ == "__main__":
    unittest.main()
