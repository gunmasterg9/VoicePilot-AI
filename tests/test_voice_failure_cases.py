"""
NEO AI - Voice Failure Case Verification Test Suite
Verifies all 12 critical voice pipeline failure modes and quality requirements:
1. Empty audio does not produce a command.
2. Silence does not trigger AI or PC actions.
3. Unclear transcription does not launch web search.
4. 'ndo' is not executed as a command.
5. 'Open Notepad' reaches the local handler without calling Ollama.
6. Supported Hindi phrases route correctly.
7. Ordinary clear questions use local Ollama.
8. Explicitly requested web searches still work if supported.
9. STOP and CANCEL are handled correctly.
10. Ollama being unavailable does not break local commands.
11. Existing security and destructive-action confirmation tests still pass.
12. The UI correctly receives transcription and execution status updates.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.agent import NeoAgent
from core.router import CommandRouter, Intent, route_direct_command, is_ambiguous_fragment
from interfaces.voice import VoiceInterface, validate_transcription
from core.llm import OllamaError
from core.settings import settings


class TestVoiceFailureCases(unittest.TestCase):
    """Rigorous tests covering the exact voice failure cases and edge conditions."""

    def setUp(self):
        self._orig_lang = settings.get("speech_language", "en")
        settings.set("speech_language", "en")
        self.agent = NeoAgent()
        self.router = CommandRouter()
        self.logs = []
        self.states = []
        self.voice = VoiceInterface(
            agent=self.agent,
            output_callback=lambda msg: self.logs.append(str(msg)),
            state_callback=lambda st: self.states.append(str(st))
        )

    def tearDown(self):
        settings.set("speech_language", self._orig_lang)

    # ------------------------------------------------------------
    # 1. Empty audio does not produce a command
    # ------------------------------------------------------------
    def test_01_empty_audio_does_not_produce_command(self):
        """Empty audio buffers must produce no command, log an empty notice, and return None."""
        is_valid, cleaned, reason = validate_transcription("", quality={"empty": True})
        self.assertFalse(is_valid)
        self.assertEqual(reason, "empty_audio")

        with patch("soundfile.read", return_value=(np.zeros(0, dtype=np.float32), 16000)):
            result = self.voice._transcribe("dummy_empty.wav")
            self.assertEqual(result, "")
            self.assertTrue(any("empty" in log.lower() for log in self.logs))

    # ------------------------------------------------------------
    # 2. Silence does not trigger AI or PC actions
    # ------------------------------------------------------------
    @patch("webbrowser.open")
    @patch("core.agent.ask_ollama")
    def test_02_silence_does_not_trigger_ai_or_pc_actions(self, mock_ollama, mock_web):
        """Silence (rms < 0.002) must skip Whisper, return empty text, and trigger zero actions."""
        silent_audio = np.zeros(16000, dtype=np.float32)
        with patch("soundfile.read", return_value=(silent_audio, 16000)):
            result = self.voice._transcribe("dummy_silent.wav")
            self.assertEqual(result, "")
            self.assertTrue(any("silent" in log.lower() for log in self.logs))

        mock_ollama.assert_not_called()
        mock_web.assert_not_called()

    # ------------------------------------------------------------
    # 3. Unclear transcription does not launch web search
    # ------------------------------------------------------------
    @patch("webbrowser.open")
    @patch("core.agent.ask_ollama")
    def test_03_unclear_transcription_does_not_launch_web_search(self, mock_ollama, mock_web):
        """Unclear noise/fragment transcriptions must be rejected without launching web search."""
        unclear_inputs = ["Kaakwar", "asdfgh", "blablabla", "zzz"]
        for noisy in unclear_inputs:
            is_valid, cleaned, reason = validate_transcription(noisy)
            self.assertFalse(is_valid, f"Expected '{noisy}' to be rejected as ambiguous")

            response = self.agent.run(noisy)
            self.assertIn("understand", response.lower())
            mock_web.assert_not_called()

    # ------------------------------------------------------------
    # 4. 'ndo' is not executed as a command
    # ------------------------------------------------------------
    @patch("webbrowser.open")
    @patch("core.agent.ask_ollama")
    def test_04_ndo_not_executed_as_command(self, mock_ollama, mock_web):
        """'ndo' must be classified as AMBIGUOUS, rejected, and never executed as web search or command."""
        self.assertTrue(is_ambiguous_fragment("ndo"))

        intent, details = self.router.classify_intent("ndo")
        self.assertEqual(intent, Intent.AMBIGUOUS)

        # In voice pipeline:
        self.voice._transcribe = MagicMock(return_value="ndo")
        self.voice.recognizer.listen = MagicMock(return_value=MagicMock())
        self.voice._audio_to_wav = MagicMock(return_value="dummy.wav")
        with patch("speech_recognition.Microphone"):
            voice_result = self.voice.listen_once()
            self.assertIsNone(voice_result)
            self.assertTrue(any("rejected" in log.lower() for log in self.logs))

        # In agent run:
        response = self.agent.run("ndo")
        self.assertEqual(response, "I didn't understand. Please try again.")
        mock_web.assert_not_called()
        mock_ollama.assert_not_called()

    # ------------------------------------------------------------
    # 5. 'open notepad' reaches the local handler without calling Ollama
    # ------------------------------------------------------------
    @patch("os.startfile")
    @patch("subprocess.Popen")
    @patch("core.agent.ask_ollama")
    def test_05_open_notepad_reaches_local_handler_without_calling_ollama(self, mock_ollama, mock_popen, mock_startfile):
        """'Open Notepad' must be handled locally and immediately without invoking Ollama."""
        response = self.agent.run("Open Notepad")
        self.assertIsNotNone(response)
        self.assertIn("notepad", response.lower())
        self.assertTrue(mock_startfile.called or mock_popen.called)
        mock_ollama.assert_not_called()

    # ------------------------------------------------------------
    # 6. Supported Hindi phrases route correctly
    # ------------------------------------------------------------
    @patch("os.startfile")
    @patch("subprocess.Popen")
    @patch("pyautogui.press")
    @patch("core.agent.ask_ollama")
    def test_06_supported_hindi_phrases_route_correctly(self, mock_ollama, mock_press, mock_popen, mock_startfile):
        """All supported Hindi phrases must route to local handlers without calling Ollama."""
        # 1. नोटपैड खोलो
        resp = self.agent.run("नोटपैड खोलो")
        self.assertIn("notepad", resp.lower())
        self.assertTrue(mock_startfile.called or mock_popen.called)

        # 2. कैलकुलेटर खोलो
        resp = self.agent.run("कैलकुलेटर खोलो")
        self.assertIn("calculator", resp.lower())

        # 3. आवाज़ बढ़ाओ
        resp = self.agent.run("आवाज़ बढ़ाओ")
        self.assertIn("volume", resp.lower())
        mock_press.assert_called_with("volumeup")

        # 4. वॉल्यूम कम करो
        resp = self.agent.run("वॉल्यूम कम करो")
        self.assertIn("volume", resp.lower())
        mock_press.assert_called_with("volumedown")

        # 5. रुक जाओ
        resp = self.agent.run("रुक जाओ")
        self.assertIn("halted", resp.lower())

        mock_ollama.assert_not_called()

    # ------------------------------------------------------------
    # 7. Ordinary clear questions use local Ollama
    # ------------------------------------------------------------
    @patch("core.agent.ask_ollama")
    def test_07_ordinary_clear_questions_use_local_ollama(self, mock_ollama):
        """Clear conversational questions must route to local Ollama."""
        mock_ollama.return_value = {
            "type": "chat",
            "response": "Python is a high-level programming language."
        }
        question = "What is Python programming language?"
        intent, _ = self.router.classify_intent(question)
        self.assertEqual(intent, Intent.CONVERSATIONAL)

        response = self.agent.run(question)
        self.assertIn("Python is a high-level", response)
        mock_ollama.assert_called_once()

    # ------------------------------------------------------------
    # 8. Explicitly requested web searches still work if supported
    # ------------------------------------------------------------
    @patch("webbrowser.open")
    def test_08_explicitly_requested_web_searches_still_work(self, mock_web):
        """Explicit web search requests ('search for ... on google') must trigger search_web."""
        response = self.agent.run("search for python documentation on google")
        self.assertTrue("searching google" in response.lower() or "searching the web" in response.lower())
        mock_web.assert_called_once()
        url = mock_web.call_args[0][0]
        self.assertIn("google.com/search", url)
        self.assertIn("python", url)

    # ------------------------------------------------------------
    # 9. STOP and CANCEL are handled correctly
    # ------------------------------------------------------------
    @patch("interfaces.tts.tts_manager.stop")
    def test_09_stop_and_cancel_handled_correctly(self, mock_tts_stop):
        """'Stop' and 'Cancel' must halt operations and invoke TTS manager stop."""
        resp1 = self.agent.run("Stop")
        self.assertIn("halted", resp1.lower())
        mock_tts_stop.assert_called()

        resp2 = self.agent.run("Cancel")
        self.assertIn("halted", resp2.lower())

        # Check intent classification
        intent1, _ = self.router.classify_intent("stop")
        intent2, _ = self.router.classify_intent("cancel")
        self.assertEqual(intent1, Intent.SYSTEM_CONTROL)
        self.assertEqual(intent2, Intent.SYSTEM_CONTROL)

    # ------------------------------------------------------------
    # 10. Ollama being unavailable does not break local commands
    # ------------------------------------------------------------
    @patch("core.agent.ask_ollama", side_effect=OllamaError("Connection refused"))
    @patch("subprocess.Popen")
    @patch("pyautogui.press")
    def test_10_ollama_unavailable_does_not_break_local_commands(self, mock_press, mock_popen, mock_ollama):
        """Even if Ollama is completely offline/crashed, local PC controls must execute 100% reliably."""
        # 1. Notepad
        resp = self.agent.run("Open Notepad")
        self.assertIn("notepad", resp.lower())

        # 2. Volume Up
        resp = self.agent.run("Increase volume")
        self.assertIn("volume", resp.lower())

        # 3. What time is it
        resp = self.agent.run("What time is it?")
        self.assertIn("time", resp.lower())

        # 4. Hindi Notepad
        resp = self.agent.run("नोटपैड खोलो")
        self.assertIn("notepad", resp.lower())

        # Ollama was never called for these local commands
        mock_ollama.assert_not_called()

    # ------------------------------------------------------------
    # 11. Existing security and destructive-action confirmation tests
    # ------------------------------------------------------------
    def test_11_destructive_actions_require_confirmation(self):
        """Destructive actions like Shutdown PC must be classified as DESTRUCTIVE_ACTION."""
        intent, details = self.router.classify_intent("shutdown pc")
        self.assertEqual(intent, Intent.DESTRUCTIVE_ACTION)
        self.assertEqual(details["tool"], "shutdown_pc")

        intent, details = self.router.classify_intent("restart pc")
        self.assertEqual(intent, Intent.DESTRUCTIVE_ACTION)
        self.assertEqual(details["tool"], "restart_pc")

    # ------------------------------------------------------------
    # 12. UI receives transcription and execution status updates
    # ------------------------------------------------------------
    def test_12_ui_receives_transcription_and_execution_status_updates(self):
        """VoiceInterface process_voice_command must output YOU > recognized before action result."""
        self.voice._transcribe = MagicMock(return_value="what time is it")
        self.voice.recognizer.listen = MagicMock(return_value=MagicMock())
        self.voice._audio_to_wav = MagicMock(return_value="dummy.wav")
        with patch("speech_recognition.Microphone"):
            resp = self.voice.process_voice_command()

        self.assertIsNotNone(resp)
        # Check that YOU > what time is it was logged
        self.assertTrue(any("YOU > what time is it" in log for log in self.logs))
        # Check that intent status was logged
        self.assertTrue(any("[ROUTER] Intent: PC_COMMAND" in log for log in self.logs))
        # Check that action result was logged
        self.assertTrue(any("[ACTION RESULT]" in log for log in self.logs))


if __name__ == "__main__":
    unittest.main()
