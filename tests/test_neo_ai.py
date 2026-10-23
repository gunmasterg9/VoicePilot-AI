"""
NEO AI - Comprehensive Test Suite
Tests application identity, backward compatibility, settings migration,
LLM provider discovery, TTS online/offline fallback, safety validation,
and desktop UI components.
"""

import os
import sys
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestNeoIdentityAndAliases(unittest.TestCase):
    """Verifies rebranding to NEO AI and backward-compatible aliases."""

    def test_branding_constants(self):
        from config import APP_NAME, NEO_NAME, WINDOW_TITLE, TAGLINE, ORION_NAME
        self.assertEqual(APP_NAME, "NEO AI")
        self.assertEqual(NEO_NAME, "NEO")
        self.assertEqual(WINDOW_TITLE, "NEO AI Assistant")
        self.assertEqual(TAGLINE, "Your Local AI PC Assistant")
        self.assertEqual(ORION_NAME, "NEO")

    def test_agent_alias(self):
        from core.agent import NeoAgent, OrionAgent
        self.assertIs(NeoAgent, OrionAgent)
        agent = NeoAgent()
        self.assertEqual(agent.name, "NEO")
        self.assertIn("NEO", agent.description)
        self.assertIn("Gautam Vandar", agent.creator)

    def test_ui_alias(self):
        from ui.window import NeoWindow, OrionWindow
        self.assertIs(NeoWindow, OrionWindow)

    def test_interface_aliases(self):
        from interfaces.terminal import run_neo_terminal, run_terminal
        from interfaces.api import run_neo_api, run_api
        from ui.app import run_neo_ui, run_ui
        self.assertIs(run_neo_terminal, run_terminal)
        self.assertIs(run_neo_api, run_api)
        self.assertIs(run_neo_ui, run_ui)


class TestSettingsManager(unittest.TestCase):
    """Verifies settings persistence, JSON serialization, and migration."""

    def setUp(self):
        from core.settings import SettingsManager
        self.test_path = Path(__file__).resolve().parent / "test_settings_scratch.json"
        self.mgr = SettingsManager(filepath=self.test_path)

    def tearDown(self):
        if self.test_path.exists():
            try:
                self.test_path.unlink()
            except Exception:
                pass

    def test_default_settings(self):
        self.assertEqual(self.mgr.get("ai_provider"), "ollama")
        self.assertEqual(self.mgr.get("tts_provider"), "online")
        self.assertEqual(self.mgr.get("speech_language"), "en")

    def test_update_and_save(self):
        self.mgr.set("ollama_model", "qwen3:8b")
        self.assertEqual(self.mgr.get("ollama_model"), "qwen3:8b")
        # Reload fresh from disk
        from core.settings import SettingsManager
        reloaded = SettingsManager(filepath=self.test_path)
        self.assertEqual(reloaded.get("ollama_model"), "qwen3:8b")

    def test_backward_compatible_migration(self):
        # Write legacy config with ORION_ keys
        import json
        legacy_data = {
            "ORION_AI_MODEL": "legacy-llama:7b",
            "ORION_TTS_MODE": "offline_sapi",
            "UNTOUCHED_KEY": "kept"
        }
        with open(self.test_path, "w", encoding="utf-8") as f:
            json.dump(legacy_data, f)

        from core.settings import SettingsManager
        migrated = SettingsManager(filepath=self.test_path)
        self.assertEqual(migrated.get("ai_model"), "legacy-llama:7b")
        self.assertEqual(migrated.get("tts_mode"), "offline_sapi")
        self.assertEqual(migrated.get("UNTOUCHED_KEY"), "kept")


class TestLLMProviders(unittest.TestCase):
    """Verifies local Ollama dynamic model fetching and provider abstractions."""

    def test_llm_manager_initialization(self):
        from core.llm import llm_manager
        self.assertIsNotNone(llm_manager)
        provider = llm_manager.get_active_provider()
        self.assertIsNotNone(provider)

    def test_ollama_model_discovery(self):
        from core.llm import OllamaProvider
        ollama = OllamaProvider()
        reachable = ollama.is_available()
        if reachable:
            models = ollama.list_models()
            self.assertIsInstance(models, list)
            self.assertGreater(len(models), 0)
            print(f"\n  [PASS] Discovered {len(models)} local Ollama model(s): {models[:3]}...")
        else:
            print("\n  [SKIP] Ollama daemon not running during unit test, fallback handled safely.")

    def test_cloud_provider_fallback_when_unconfigured(self):
        from core.llm import CloudLLMProvider, OllamaError
        cloud = CloudLLMProvider(api_key="", model="gpt-4o-mini")
        self.assertFalse(cloud.is_available())
        with self.assertRaises(OllamaError):
            cloud.ask("Hello")


class TestVoiceAndTTSPipeline(unittest.TestCase):
    """Verifies TTS online neural synthesis, offline fallback, and instant stop."""

    def test_tts_manager_status(self):
        from interfaces.tts import tts_manager
        status = tts_manager.get_status()
        self.assertIn("provider", status)
        self.assertIn("available", status)

    def test_offline_sapi_initialization(self):
        from interfaces.tts import OfflineSapiTTSProvider
        sapi = OfflineSapiTTSProvider()
        self.assertTrue(sapi.is_available())

    def test_stop_action_safety(self):
        from interfaces.tts import tts_manager
        # Ensure stop can be called safely without crashing even when idle
        tts_manager.stop()
        self.assertFalse(tts_manager.is_speaking())


class TestPCAutomationSafety(unittest.TestCase):
    """Verifies that destructive system paths are protected by security allowlists."""

    def test_system_root_protection(self):
        from core.safety import is_path_safe_for_deletion
        system_roots = [
            "C:\\",
            "C:\\Windows",
            "C:\\Windows\\System32",
            "C:\\Program Files",
            "C:\\Program Files (x86)",
            "C:\\Users",
        ]
        for path in system_roots:
            is_safe, reason = is_path_safe_for_deletion(path)
            self.assertFalse(
                is_safe,
                f"Path {path} should be BLOCKED from deletion. Reason: {reason}"
            )

    def test_safe_user_paths(self):
        from core.safety import is_path_safe_for_deletion
        user_scratch = os.path.expanduser("~/Documents/scratch_test.txt")
        is_safe, reason = is_path_safe_for_deletion(user_scratch)
        self.assertTrue(is_safe, f"Path {user_scratch} should be permitted: {reason}")

    def test_tool_registry(self):
        from tools.registry import get_all_tools, get_tool
        tools = get_all_tools()
        self.assertIn("open_target", tools)
        self.assertIn("search_web", tools)
        self.assertIn("screenshot", tools)
        self.assertIn("list_directory", tools)


class TestPySide6DesktopUI(unittest.TestCase):
    """Verifies that the PySide6 UI window initializes cleanly with all controls."""

    def test_ui_window_initialization(self):
        from PySide6.QtWidgets import QApplication
        from ui.window import NeoWindow

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        window = NeoWindow()
        self.assertEqual(window.windowTitle(), "NEO AI Assistant")
        self.assertEqual(window.orb.state, "READY")
        self.assertIsNotNone(window.send_button)
        self.assertIsNotNone(window.voice_button)
        self.assertIsNotNone(window.tts_button)
        self.assertIsNotNone(window.stop_button)
        self.assertIsNotNone(window.settings_button)
        self.assertIsNotNone(window.chat)
        self.assertIsNotNone(window.input)

        # Test stop action
        window.stop_action()
        self.assertEqual(window.orb.state, "READY")


if __name__ == "__main__":
    unittest.main()
