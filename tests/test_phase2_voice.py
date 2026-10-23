"""
NEO AI - Phase 2 Multilingual Voice & Audio Reliability Test Suite
Verifies:
1. Voice catalog filtering by language (English, Hindi, Gujarati).
2. Explicit rejection of missing/unsupported voices (no silent substitution).
3. Online-to-offline SAPI5 fallback upon network/synthesis failure.
4. Output audio device discovery and routing.
5. Real-time volume scaling and speech rate configuration.
6. Instant stop-speaking control.
7. Multilingual Whisper model selection (tiny vs tiny.en).
8. Configuration persistence and roundtrip loading.
"""

import os
import sys
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestVoiceCatalogAndFiltering(unittest.TestCase):
    """Verifies candidate voices and dynamic language filtering."""

    def test_candidate_voices_present(self):
        from interfaces.tts import SUPPORTED_NEURAL_VOICES, ALL_NEURAL_VOICE_NAMES
        
        expected_candidates = {
            "en-US-AriaNeural",
            "en-US-GuyNeural",
            "hi-IN-SwaraNeural",
            "hi-IN-MadhurNeural",
            "gu-IN-DhwaniNeural",
            "gu-IN-NiranjanNeural"
        }
        for voice in expected_candidates:
            self.assertIn(voice, ALL_NEURAL_VOICE_NAMES, f"Candidate voice {voice} missing from catalog")

    def test_language_filtering(self):
        from interfaces.tts import SUPPORTED_NEURAL_VOICES
        
        # English filtering
        en_voices = [name for _, name in SUPPORTED_NEURAL_VOICES["en"]]
        self.assertIn("en-US-AriaNeural", en_voices)
        self.assertIn("en-US-GuyNeural", en_voices)
        self.assertNotIn("hi-IN-SwaraNeural", en_voices)
        self.assertNotIn("gu-IN-DhwaniNeural", en_voices)

        # Hindi filtering
        hi_voices = [name for _, name in SUPPORTED_NEURAL_VOICES["hi"]]
        self.assertIn("hi-IN-SwaraNeural", hi_voices)
        self.assertIn("hi-IN-MadhurNeural", hi_voices)
        self.assertNotIn("en-US-AriaNeural", hi_voices)

        # Gujarati filtering
        gu_voices = [name for _, name in SUPPORTED_NEURAL_VOICES["gu"]]
        self.assertIn("gu-IN-DhwaniNeural", gu_voices)
        self.assertIn("gu-IN-NiranjanNeural", gu_voices)
        self.assertNotIn("en-US-GuyNeural", gu_voices)

    def test_missing_voice_raises_error_no_silent_substitution(self):
        from interfaces.tts import OnlineNeuralTTSProvider
        provider = OnlineNeuralTTSProvider()
        with self.assertRaises(ValueError):
            provider.set_voice("non-existent-fantasy-voice-1234")


class TestAudioOutputRoutingAndControls(unittest.TestCase):
    """Verifies output device query, routing, volume, and rate controls."""

    def test_output_device_enumeration(self):
        from interfaces.tts import TTSManager
        devices = TTSManager.get_available_output_devices()
        self.assertIsInstance(devices, list)
        self.assertGreater(len(devices), 0, "Expected at least one audio output device on Windows")
        first_idx, first_name = devices[0]
        self.assertIsInstance(first_idx, int)
        self.assertIsInstance(first_name, str)

    def test_volume_and_rate_setters(self):
        from interfaces.tts import TTSManager
        mgr = TTSManager()
        
        mgr.set_volume(0.75)
        self.assertEqual(mgr.online_provider._volume, 0.75)
        self.assertEqual(mgr.offline_provider._volume, 0.75)

        mgr.set_rate(210)
        self.assertEqual(mgr.online_provider._rate, 210)
        self.assertEqual(mgr.offline_provider._rate, 210)

        # Test output device routing setter
        mgr.set_output_device(first_device_idx := 0)
        self.assertEqual(mgr.online_provider._output_device, 0)

    def test_instant_stop_control(self):
        from interfaces.tts import tts_manager
        tts_manager.stop()
        self.assertFalse(tts_manager.is_speaking())


class TestOnlineToOfflineTTSFallback(unittest.TestCase):
    """Verifies automatic offline fallback when online synthesis encounters failure."""

    def test_fallback_to_sapi_on_network_failure(self):
        from interfaces.tts import TTSManager
        
        log_messages = []
        mgr = TTSManager(log_callback=lambda msg: log_messages.append(msg))
        
        # Simulate online provider failure by pointing to an invalid dummy voice that errors
        mgr.online_provider._voice = "invalid-voice"
        
        # speak() should catch the error and cleanly switch to offline SAPI5 provider
        result = mgr.speak("Testing offline SAPI fallback.")
        self.assertTrue(result, "Offline fallback should succeed when online provider fails")
        self.assertEqual(mgr._current_provider_name, mgr.offline_provider.provider_name)
        self.assertTrue(any("FALLBACK" in msg for msg in log_messages))


class TestMultilingualWhisperModelSelection(unittest.TestCase):
    """Verifies automatic selection between tiny.en and multilingual tiny."""

    def test_multilingual_selection_for_indic_languages(self):
        from core.settings import settings
        from interfaces.voice import VoiceInterface
        from unittest.mock import MagicMock

        mock_agent = MagicMock()
        voice = VoiceInterface(agent=mock_agent)

        # 1. When language is English, tiny.en is appropriate
        settings.set("speech_language", "en", save=False)
        voice._load_whisper_model("tiny.en")
        self.assertEqual(voice._current_whisper_model_name, "tiny.en")

        # 2. When language is switched to Gujarati or Hindi, automatically upgrades to multilingual tiny
        settings.set("speech_language", "gu", save=False)
        voice._load_whisper_model("tiny.en")
        self.assertEqual(voice._current_whisper_model_name, "tiny")

        # 3. When language is switched to Hindi
        settings.set("speech_language", "hi", save=False)
        voice._load_whisper_model("tiny.en")
        self.assertEqual(voice._current_whisper_model_name, "tiny")

        # Reset setting to en
        settings.set("speech_language", "en", save=False)


class TestSettingsPersistencePhase2(unittest.TestCase):
    """Verifies that Phase 2 voice settings persist cleanly."""

    def setUp(self):
        from core.settings import SettingsManager
        self.test_path = Path(__file__).resolve().parent / "test_phase2_settings.json"
        self.mgr = SettingsManager(filepath=self.test_path)

    def tearDown(self):
        if self.test_path.exists():
            try:
                self.test_path.unlink()
            except Exception:
                pass

    def test_phase2_keys_roundtrip(self):
        self.mgr.set("tts_output_device_index", 3)
        self.mgr.set("tts_volume", 0.85)
        self.mgr.set("tts_speech_rate", 200)
        self.mgr.set("tts_voice_online", "gu-IN-DhwaniNeural")

        from core.settings import SettingsManager
        reloaded = SettingsManager(filepath=self.test_path)
        self.assertEqual(reloaded.get("tts_output_device_index"), 3)
        self.assertEqual(reloaded.get("tts_volume"), 0.85)
        self.assertEqual(reloaded.get("tts_speech_rate"), 200)
        self.assertEqual(reloaded.get("tts_voice_online"), "gu-IN-DhwaniNeural")


if __name__ == "__main__":
    unittest.main()
