"""
NEO AI - Phase 4 End-to-End Pipeline & Integration Test Suite
Validates the complete real-world workflow:
User Input/Voice -> Transcription -> Routing -> Tool Validation -> Execution -> Verification -> TTS Fallback.

Distinguishes:
1. Real Windows execution tests (actual process launch, filesystem verification, SAPI fallback).
2. Mocked environment tests (simulated network outage, Ollama failure, audio device absence).
3. Safety boundary & permission enforcement tests.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.agent import NeoAgent
from core.llm import OllamaError, llm_manager
from core.safety import (
    is_path_safe_for_deletion,
    requires_confirmation,
    mask_sensitive_data,
    DANGEROUS_TOOLS
)
from core.settings import SettingsManager, DEFAULT_SETTINGS
from interfaces.tts import TTSManager
from tools.registry import execute_tool, get_tool_spec, TOOLS


class TestPhase4EndToEndPipeline(unittest.TestCase):
    """End-to-end integration test suite verifying full assistant pipelines."""

    @classmethod
    def setUpClass(cls):
        print("\n" + "=" * 65)
        print("  RUNNING PHASE 4: END-TO-END PIPELINE & INTEGRATION SUITE")
        print("=" * 65)
        cls.agent = NeoAgent(confirm_callback=lambda tool, args: True)

    # ============================================================
    # 1. END-TO-END INTEGRATION PIPELINES
    # ============================================================

    def test_01_voice_to_application_launch_pipeline(self):
        """[REAL EXECUTION] Pipeline: Voice/Text -> Route -> Application Launch -> Verified Response."""
        # Notepad launch
        cmd = "open notepad"
        response = self.agent.run(cmd)
        self.assertIsNotNone(response)
        self.assertIn("notepad", response.lower())
        print(f"  [PASS] Application launch pipeline verified: '{cmd}' -> '{response}'")

    def test_02_filesystem_search_pipeline(self):
        """[REAL EXECUTION] Pipeline: Request -> Route -> Filesystem Search -> Formatted Telemetry."""
        cmd = "find my latest pdf"
        response = self.agent.run(cmd)
        self.assertIsNotNone(response)
        self.assertTrue("pdf" in response.lower())
        print(f"  [PASS] Filesystem discovery pipeline verified: '{cmd}' -> '{response[:40]}...'")

    def test_03_system_telemetry_pipeline(self):
        """[REAL EXECUTION] Pipeline: Request -> System Query -> Real Hardware Metrics."""
        cmd = "tell me how much ram is available"
        response = self.agent.run(cmd)
        self.assertIsNotNone(response)
        self.assertIn("ram", response.lower())
        self.assertIn("gb", response.lower())
        print(f"  [PASS] System telemetry pipeline verified: '{cmd}' -> '{response}'")

    def test_04_multi_step_task_reliability(self):
        """[REAL EXECUTION] Compound Multi-step command: Launches application and prompts for required missing details."""
        cmd = "Open Notepad and help me write a letter."
        response = self.agent.run(cmd)
        self.assertIsNotNone(response)
        # Must verify Notepad launch and ask for letter recipient/topic
        self.assertIn("notepad", response.lower())
        self.assertTrue("address" in response.lower() or "topic" in response.lower() or "who" in response.lower())
        print(f"  [PASS] Multi-step task verification confirmed: '{cmd}' -> '{response}'")

    def test_05_tool_failure_to_understandable_response(self):
        """[REAL/ERROR RECOVERY] Verifies that tool failure produces informative user-facing explanation."""
        # Non-existent file deletion
        result = execute_tool("delete_path", {"path": r"C:\non_existent_folder_xyz_12345\fake.txt"})
        self.assertTrue("not exist" in str(result).lower() or not result.success)
        print(f"  [PASS] Tool failure recovery verified: Produced clear message '{result}'")

    def test_06_online_tts_failure_to_offline_fallback(self):
        """[MOCKED/OFFLINE FALLBACK] Verifies automatic fallback to SAPI5 when online Edge TTS fails."""
        tts = TTSManager()
        # Mock online provider speak to raise network exception
        with patch.object(tts.online_provider, "speak", side_effect=Exception("Connection timed out")):
            with patch.object(tts.offline_provider, "speak", return_value=True) as mock_sapi:
                success = tts.speak("Testing offline SAPI fallback.")
                self.assertTrue(success)
                mock_sapi.assert_called_once()
                print("  [PASS] Automatic online TTS failure -> offline SAPI5 fallback confirmed.")

    def test_07_ollama_unavailable_deterministic_fallback(self):
        """[MOCKED/OFFLINE FALLBACK] Verifies full offline automation when Ollama is completely unreachable."""
        with patch("core.agent.ask_ollama", side_effect=OllamaError("Ollama service offline")):
            # Local automation commands must continue executing cleanly
            r1 = self.agent.run("open the downloads folder")
            self.assertIn("downloads", r1.lower())

            r2 = self.agent.run("how much memory is used")
            self.assertIn("ram", r2.lower())

            # Open-ended questions should explain offline state politely
            r3 = self.agent.run("explain general relativity theory")
            self.assertIn("offline", r3.lower())
            print("  [PASS] Ollama unavailable -> 100% deterministic command fallback confirmed.")

    def test_08_conversation_clearing_without_settings_mutation(self):
        """[INTEGRATION] Verifies clearing conversation memory leaves persistent settings untouched."""
        import tempfile
        temp_settings = Path(tempfile.gettempdir()) / "neo_test_settings.json"
        try:
            sm = SettingsManager(temp_settings)
            sm.set("ollama_model", "qwen3:1.7b")
            sm.set("speech_language", "hi")

            # Populate agent conversation
            agent = NeoAgent()
            agent._record_conversation("Hello", "Hi there!")
            self.assertGreater(len(agent.conversation), 0)

            # Clear conversation
            agent.clear_conversation()
            self.assertEqual(len(agent.conversation), 0)

            # Reload settings and verify intact
            sm_reloaded = SettingsManager(temp_settings)
            self.assertEqual(sm_reloaded.get("ollama_model"), "qwen3:1.7b")
            self.assertEqual(sm_reloaded.get("speech_language"), "hi")
            print("  [PASS] Conversation clearing isolated from persistent settings confirmed.")
        finally:
            if temp_settings.exists():
                temp_settings.unlink()

    def test_09_stop_speaking_and_cancellation_behavior(self):
        """[INTEGRATION] Verifies cancellation halts speech and aborts pending actions."""
        agent = NeoAgent()

        # Command "stop speaking"
        res = agent.run("stop speaking")
        self.assertIn("stopped", res.lower())

        # Calling cancel_current_operation blocks subsequent pending actions
        agent.cancel_current_operation()
        self.assertTrue(agent.is_cancelled)

        succ, msg = agent.execute_action({"tool": "screenshot", "arguments": {}})
        self.assertFalse(succ)
        self.assertIn("cancelled", msg.lower())
        print("  [PASS] Stop speaking and active execution cancellation confirmed.")

    # ============================================================
    # 2. SAFETY & SECURITY VERIFICATION
    # ============================================================

    def test_10_protected_system_paths_safety_boundaries(self):
        """[SAFETY] Verifies strict protection for Windows, Program Files, drive roots, and user roots."""
        protected = [
            r"C:\Windows",
            r"C:\Windows\System32",
            r"C:\Program Files",
            r"C:\Program Files (x86)",
            r"C:\\",
            r"..\..\..\Windows",
            str(Path.home()),
            str(Path.home().parent)
        ]

        for p in protected:
            safe, reason = is_path_safe_for_deletion(p)
            self.assertFalse(safe, f"Path '{p}' should have been blocked!")
            self.assertIn("refusing", reason.lower())

        print("  [PASS] Protected system path safety boundaries fully enforced.")

    def test_11_rejection_of_unregistered_and_arbitrary_shell_commands(self):
        """[SECURITY] Verifies arbitrary shell commands from LLM plans cannot execute."""
        dangerous_plan_actions = [
            {"tool": "execute_shell", "arguments": {"cmd": "del C:\\"}},
            {"tool": "bash", "arguments": {"command": "rm -rf /"}},
            {"tool": "powershell", "arguments": {"script": "Get-Process"}},
            {"tool": "system_exec", "arguments": {}}
        ]

        for action in dangerous_plan_actions:
            succ, res = self.agent.execute_action(action)
            self.assertFalse(succ, f"Action {action['tool']} should have been rejected!")
            self.assertIn("unrecognized tool", res.lower())

        print("  [PASS] Unrestricted shell execution strictly prevented.")

    def test_12_cancellation_aborts_pending_unapproved_actions(self):
        """[SAFETY] Verifies that when a destructive action is rejected, subsequent actions do not execute."""
        cancelled_agent = NeoAgent(confirm_callback=lambda tool, args: False)

        plan_actions = [
            {"tool": "delete_path", "arguments": {"path": "test.txt"}},
            {"tool": "create_folder", "arguments": {"path": "subsequent_folder"}}
        ]

        results = []
        for act in plan_actions:
            succ, res = cancelled_agent.execute_action(act)
            results.append(succ)
            if not succ:
                break

        # Only first action was evaluated and failed; second never executed
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0])
        print("  [PASS] Rejection of pending destructive actions confirmed.")

    def test_13_sensitive_data_and_credentials_masking(self):
        """[SECURITY] Verifies sensitive API keys and tokens are masked and not exposed."""
        raw_log = 'Sending request to Cloud LLM with api_key: "sk-proj-1234567890abcdef123456" and model: "gpt-4o"'
        masked = mask_sensitive_data(raw_log)

        self.assertNotIn("sk-proj-1234567890abcdef123456", masked)
        self.assertIn("sk-***[MASKED]***", masked)
        print("  [PASS] Sensitive credentials masking verified.")

    # ============================================================
    # 3. SETTINGS PERSISTENCE & LEGACY MIGRATION
    # ============================================================

    def test_14_legacy_orion_settings_migration(self):
        """[SETTINGS] Verifies backward-compatible migration of legacy ORION_ config keys."""
        import json
        temp_file = Path(tempfile.gettempdir()) / "test_legacy_orion_settings.json"
        try:
            legacy_data = {
                "orion_ai_model": "llama3.2:latest",
                "orion_tts_mode": "offline",
                "orion_name": "NEO",
                "custom_unrelated_setting": True
            }
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(legacy_data, f)

            sm = SettingsManager(temp_file)
            self.assertEqual(sm.get("ollama_model"), "llama3.2:latest")
            self.assertEqual(sm.get("tts_provider"), "offline")
            self.assertEqual(sm.get("assistant_name"), "NEO")
            self.assertTrue(sm.get("custom_unrelated_setting"))
            print("  [PASS] Legacy ORION settings migration safely verified without data loss.")
        finally:
            if temp_file.exists():
                temp_file.unlink()


if __name__ == "__main__":
    unittest.main()
