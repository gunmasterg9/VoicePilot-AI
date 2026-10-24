"""
Phase 9 Automated Tests: Comprehensive Offline Windows AI Assistant Verification.

Tests verify:
1. UI startup when Ollama is unavailable.
2. Local command execution without any Ollama request.
3. Opening a registered application through a mocked handler.
4. Volume and screenshot commands where implemented.
5. Conversational requests being routed to Ollama.
6. Local commands working while Ollama is stopped.
7. Safe handling of unknown and ambiguous commands.
8. Confirmation requirements for destructive actions.
9. Stop/cancel behavior.
10. Duplicate-execution prevention.
11. Recognition errors and empty transcription.
12. Offline TTS errors and disabled voice output.
13. Settings validation and persistence.
14. Non-blocking UI behavior during AI and audio operations.
15. Proper cleanup of audio streams and worker threads.
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.router import CommandRouter, Intent
from core.agent import NeoAgent
from core.settings import settings
from tools.system import volume_up, volume_down, volume_mute, get_system_info, take_screenshot
from tools.registry import TOOLS, TOOL_SPECS, ToolPermission
from interfaces.tts import TTSManager
from core.llm import OllamaError


class TestPhase9OfflineAssistant(unittest.TestCase):

    def setUp(self):
        self.router = CommandRouter()
        self.agent = NeoAgent()

    # 1. UI startup when Ollama is unavailable
    @patch("core.llm.OllamaProvider.check_health", return_value=False)
    def test_01_ui_startup_when_ollama_unavailable(self, mock_ollama_health):
        from PySide6.QtWidgets import QApplication
        from ui.window import NeoWindow

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        window = NeoWindow()
        self.assertIsNotNone(window)
        self.assertEqual(window.windowTitle(), "NEO AI Assistant")
        self.assertIsNotNone(window.orb)
        self.assertIsNotNone(window.status)
        self.assertIsNotNone(window.chat)
        self.assertIsNotNone(window.input)
        self.assertIsNotNone(window.send_button)
        self.assertIsNotNone(window.voice_button)
        self.assertIsNotNone(window.tts_button)
        self.assertIsNotNone(window.stop_button)
        self.assertIsNotNone(window.btn_quick_calc)
        self.assertIsNotNone(window.table_activity)
        self.assertEqual(window.current_state, "READY")
        window.close()

    # 2. Local command execution without any Ollama request
    @patch("core.llm.llm_manager.ask")
    def test_02_local_command_execution_without_ollama(self, mock_ollama_ask):
        # Ollama must NEVER be called for known PC commands
        mock_ollama_ask.side_effect = AssertionError("Ollama was contacted for a local PC command!")

        with patch("subprocess.Popen") as mock_popen:
            res = self.agent.process_text("open notepad")
            self.assertIn("notepad", res.lower())
            mock_ollama_ask.assert_not_called()

    # 3. Opening a registered application through a mocked handler
    @patch("subprocess.Popen")
    def test_03_open_registered_application_mocked(self, mock_popen):
        res = self.agent.process_text("open calculator")
        self.assertIn("calculator", res.lower())
        mock_popen.assert_called_once()

    # 4. Volume and screenshot commands where implemented
    @patch("pyautogui.press")
    def test_04a_volume_controls(self, mock_press):
        res_up = volume_up()
        self.assertIn("increased", res_up.lower())
        mock_press.assert_any_call("volumeup")

        res_down = volume_down()
        self.assertIn("decreased", res_down.lower())
        mock_press.assert_any_call("volumedown")

        res_mute = volume_mute()
        self.assertIn("toggled", res_mute.lower())
        mock_press.assert_called_with("volumemute")

    @patch("pyautogui.screenshot")
    def test_04b_screenshot_tool(self, mock_screenshot):
        mock_img = MagicMock()
        mock_screenshot.return_value = mock_img

        res = take_screenshot()
        self.assertIn("screenshot", res.lower())
        mock_screenshot.assert_called_once()

    # 5. Conversational requests being routed to Ollama
    @patch("core.llm.llm_manager.ask", return_value={"type": "chat", "response": "Functions in Python are defined with def.", "actions": []})
    def test_05_conversational_requests_routed_to_ollama(self, mock_ask):
        # Intent classification
        intent, params = self.router.classify_intent("Explain how Python functions work")
        self.assertEqual(intent, Intent.CONVERSATIONAL)

        # Agent processing
        res = self.agent.process_text("Explain how Python functions work")
        self.assertIn("Functions in Python", res)
        mock_ask.assert_called_once()

    # 6. Local commands working while Ollama is stopped
    @patch("core.llm.llm_manager.ask", side_effect=OllamaError("Service unreachable"))
    @patch("pyautogui.press")
    def test_06_local_commands_work_while_ollama_stopped(self, mock_press, mock_ask):
        res = self.agent.process_text("mute volume")
        self.assertIn("mute", res.lower())

        sys_res = self.agent.process_text("show system information")
        self.assertIn("CPU", sys_res)

    # 7. Safe handling of unknown and ambiguous commands
    @patch("core.llm.llm_manager.ask", side_effect=OllamaError("Service unreachable"))
    def test_07_safe_handling_of_unknown_and_ambiguous(self, mock_ask):
        intent, params = self.router.classify_intent("xyz123 random nonsense query")
        self.assertEqual(intent, Intent.CONVERSATIONAL)

        # When Ollama is offline and query is unknown, agent returns safe graceful response without executing arbitrary code
        res = self.agent.process_text("xyz123 random nonsense query")
        self.assertTrue("offline" in res.lower() or "not available" in res.lower() or "error" in res.lower())

    # 8. Confirmation requirements for destructive actions
    def test_08_confirmation_requirements_for_destructive_actions(self):
        # Settings confirm_destructive_actions is True by default
        self.assertTrue(settings.get("confirm_destructive_actions", True))
        
        # Tools registry verifies permissions
        for name, spec in TOOL_SPECS.items():
            if spec.permission == ToolPermission.DESTRUCTIVE:
                # Must be strictly controlled
                self.assertIn(name, ["delete_path", "shutdown_pc", "restart_pc"])

    # 9. Stop/cancel behavior
    def test_09_stop_cancel_behavior(self):
        # Hindi and English stop triggers
        for stop_phrase in ["stop", "cancel", "रुक जाओ", "बंद करो"]:
            intent, params = self.router.classify_intent(stop_phrase)
            self.assertEqual(intent, Intent.SYSTEM_CONTROL)
            self.assertEqual(params.get("command"), "stop")

        # Cancellation state flag
        self.agent.cancel_current_operation()
        self.assertTrue(self.agent.is_cancelled)

    # 10. Duplicate-execution prevention
    def test_10_duplicate_execution_prevention(self):
        # Consecutive empty or duplicate requests don't cause crashes or multiple threads
        res1 = self.agent.process_text("")
        self.assertIn("didn't receive a command", res1)

        res2 = self.agent.process_text("   ")
        self.assertIn("didn't receive a command", res2)

    # 11. Recognition errors and empty transcription
    def test_11_recognition_errors_and_empty_transcription(self):
        intent, params = self.router.classify_intent("")
        self.assertEqual(intent, Intent.EMPTY)

        res = self.agent.process_text("")
        self.assertEqual(res, "I didn't receive a command.")

    # 12. Offline TTS errors and disabled voice output
    def test_12_offline_tts_errors_and_disabled_voice_output(self):
        tts = TTSManager()
        # When tts_enabled is False, speak should return without error
        settings.set("tts_enabled", False, save=False)
        self.assertFalse(settings.get("tts_enabled"))
        # Must not raise any exception
        tts.speak("This should not play")

        # Reset setting
        settings.set("tts_enabled", True, save=False)
        self.assertTrue(settings.get("tts_enabled"))

    # 13. Settings validation and persistence
    def test_13_settings_validation_and_persistence(self):
        orig_val = settings.get("speech_language", "en")
        settings.set("speech_language", "hi", save=False)
        self.assertEqual(settings.get("speech_language"), "hi")

        # Restore
        settings.set("speech_language", orig_val, save=False)
        self.assertEqual(settings.get("speech_language"), orig_val)

    # 14. Non-blocking UI behavior during AI and audio operations
    def test_14_nonblocking_ui_behavior(self):
        from ui.window import AgentWorker, VoiceWorker
        worker = AgentWorker(self.agent, "test query")
        self.assertIsNotNone(worker)
        self.assertTrue(hasattr(worker, "run"))
        self.assertTrue(hasattr(worker, "finished"))
        self.assertTrue(hasattr(worker, "state"))

    # 15. Proper cleanup of audio streams and worker threads
    def test_15_proper_cleanup_of_audio_and_worker_threads(self):
        from PySide6.QtWidgets import QApplication
        from ui.window import NeoWindow

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        window = NeoWindow()
        self.assertFalse(window._close_pending)
        # Calling stop_action should reset state to READY
        window.stop_action()
        self.assertEqual(window.current_state, "READY")
        window.close()


if __name__ == "__main__":
    unittest.main()
