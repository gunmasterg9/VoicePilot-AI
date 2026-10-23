"""
NEO AI - Phase 3 AI Brain & PC Automation Verification Suite
Tests:
1. 30+ Natural-language command variations (Browsers, Special Folders, PDFs, RAM, compound requests)
2. Tool specifications, argument schemas, and post-condition verification
3. Safety boundary enforcement (System paths, root drive, destructive action confirmation)
4. Ollama resilience: offline rule-based fallback, JSON error recovery, and model health
5. Conversation context pruning, clearing, and operation cancellation
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.agent import NeoAgent, OrionAgent
from core.router import route_direct_command, normalize_plan
from core.llm import _extract_and_parse_json, llm_manager, OllamaError
from core.safety import (
    is_path_safe_for_deletion,
    requires_confirmation,
    confirmation_message,
    DANGEROUS_TOOLS
)
from tools.base import ToolPermission, ToolResult, ToolSpec
from tools.registry import (
    get_tool,
    get_tool_spec,
    execute_tool,
    TOOL_SPECS
)
from tools.filesystem import (
    find_latest_file,
    open_special_folder,
    create_folder,
    delete_path,
    list_directory
)
from tools.system import get_ram_info, get_system_telemetry


class TestPhase3BrainAndAutomation(unittest.TestCase):
    """Phase 3 Test Suite for NEO AI."""

    @classmethod
    def setUpClass(cls):
        print("\n" + "=" * 65)
        print("  RUNNING PHASE 3: AI BRAIN & RELIABLE PC AUTOMATION SUITE")
        print("=" * 65)
        # Agent configured to auto-confirm non-destructive and mock-confirm destructive
        cls.agent = NeoAgent(confirm_callback=lambda tool, args: True)

    # ============================================================
    # 1. 30+ NATURAL LANGUAGE COMMAND VARIATIONS
    # ============================================================

    def test_01_thirty_natural_language_command_variations(self):
        """Verify at least 30 natural-language command variations execute reliably."""
        commands = [
            # 1-7: Core Phase 3 Prompt Requirements
            ("Open my browser.", "browser"),
            ("Open the Downloads folder.", "Downloads"),
            ("Find my latest PDF.", "PDF"),
            ("Search the web for Python tutorials.", "Python tutorials"),
            ("Tell me how much RAM is available.", "RAM"),
            ("Open Notepad and help me write a letter.", "Notepad"),
            ("Stop speaking.", "Speech synthesis stopped"),

            # 8-12: Additional Folder and File Discovery Variations
            ("open downloads", "Downloads"),
            ("open my documents", "Documents"),
            ("open desktop folder", "Desktop"),
            ("open pictures folder", "Pictures"),
            ("find recent pdf", "PDF"),

            # 13-16: Web Search and Navigation Variations
            ("search for rust programming", "rust programming"),
            ("search YouTube for lo-fi beats", "lo-fi beats"),
            ("open google", "google"),
            ("open github", "github"),

            # 17-21: System Telemetry and Hardware Variations
            ("how much ram is free", "RAM"),
            ("check memory", "RAM"),
            ("check cpu usage", "CPU"),
            ("how much memory is used", "RAM"),
            ("check battery and system status", "telemetry"),

            # 22-26: Desktop Application Launching Variations
            ("open notepad", "notepad"),
            ("launch calculator", "calculator"),
            ("open file explorer", "file explorer"),
            ("open command prompt", "command prompt"),
            ("take a screenshot", "screenshot"),

            # 27-30: Identity, Attribution & Conversational Responses
            ("who are you", "NEO"),
            ("who created you", "Gautam Vandar"),
            ("what is your name", "NEO"),
            ("what can you do", "NEO"),

            # 31-33: Power and Control Commands
            ("lock the computer", "locked"),
            ("tell me a joke", ""),
            ("silence", "Speech synthesis stopped"),
        ]

        self.assertGreaterEqual(len(commands), 30, "Must test at least 30 command variations.")
        print(f"\n  Testing {len(commands)} Natural Language Command Variations:")
        print("  " + "-" * 60)

        for idx, (cmd, expected_sub) in enumerate(commands, 1):
            response = self.agent.run(cmd)
            self.assertIsNotNone(response, f"Command '{cmd}' returned None.")
            self.assertIsInstance(response, str, f"Command '{cmd}' did not return string.")
            self.assertGreater(len(response.strip()), 0, f"Command '{cmd}' returned empty response.")

            if expected_sub:
                self.assertTrue(
                    expected_sub.lower() in response.lower(),
                    f"Expected '{expected_sub}' in response for '{cmd}', got: '{response}'"
                )

            snippet = response.replace("\n", " ")[:40]
            print(f"  [{idx:02d}/{len(commands)}] '{cmd}' -> '{snippet}...'")

        print("  " + "-" * 60)
        print("  [PASS] 33/33 Natural language command variations executed successfully.")

    # ============================================================
    # 2. TOOL REGISTRY, VALIDATION & POST-CONDITIONS
    # ============================================================

    def test_02_tool_spec_contracts_and_schemas(self):
        """Verify all registered tools have valid ToolSpecs, schemas, and permissions."""
        specs = TOOL_SPECS
        self.assertGreaterEqual(len(specs), 15, "Registry missing expected tool specifications.")

        for name, spec in specs.items():
            self.assertIsInstance(spec, ToolSpec)
            self.assertEqual(spec.name, name)
            self.assertTrue(len(spec.description) > 0, f"Tool '{name}' lacks description.")
            self.assertIsInstance(spec.permission, ToolPermission)
            self.assertIsInstance(spec.parameters, dict)

        print(f"  [PASS] Verified {len(specs)} ToolSpec schemas and permission contracts.")

    def test_03_argument_validation(self):
        """Verify tool execution validates required arguments and types."""
        spec = get_tool_spec("search_web")
        self.assertIsNotNone(spec)

        # Missing required parameter 'query'
        valid, err = spec.validate_arguments({})
        self.assertFalse(valid)
        self.assertIn("query", err)

        # Valid arguments
        valid, err = spec.validate_arguments({"query": "python"})
        self.assertTrue(valid)
        self.assertIsNone(err)

        print("  [PASS] Tool argument schema validation functioning properly.")

    def test_04_filesystem_tool_post_conditions(self):
        """Verify real filesystem tool creates, verifies, lists, and safely removes directories."""
        import tempfile
        temp_dir = Path(tempfile.gettempdir()) / "neo_test_phase3_sandbox"
        try:
            # Create folder
            res_create = create_folder(str(temp_dir))
            self.assertTrue(temp_dir.is_dir(), f"Folder was not created: {res_create}")
            self.assertIn("created successfully", res_create.lower())

            # List directory
            res_list = list_directory(str(temp_dir))
            self.assertIn("empty", res_list.lower())

            # Delete folder
            res_delete = delete_path(str(temp_dir))
            self.assertFalse(temp_dir.exists(), f"Folder was not deleted: {res_delete}")
            self.assertIn("successfully deleted", res_delete.lower())
            print("  [PASS] Filesystem post-condition verification confirmed.")
        finally:
            if temp_dir.exists():
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)

    # ============================================================
    # 3. SAFETY, DESTRUCTIVE ACTIONS & PERMISSION CHECKS
    # ============================================================

    def test_05_protected_system_paths_safety(self):
        """Verify refusal to delete protected system directories and drives."""
        protected_targets = [
            r"C:\Windows",
            r"C:\Windows\System32",
            r"C:\Program Files",
            r"C:\Program Files (x86)",
            r"C:\\",
            str(Path.home()),
            str(Path.home().parent)
        ]

        for path in protected_targets:
            safe, reason = is_path_safe_for_deletion(path)
            self.assertFalse(safe, f"Safety check failed to protect: {path}")
            self.assertIn("Refusing", reason)

        print(f"  [PASS] All {len(protected_targets)} critical system paths protected against deletion.")

    def test_06_destructive_action_confirmation(self):
        """Verify destructive actions require and respect human confirmation."""
        for tool in DANGEROUS_TOOLS:
            self.assertTrue(requires_confirmation(tool), f"{tool} must require confirmation.")
            msg = confirmation_message(tool, {"path": "test.txt", "delay": 5})
            self.assertTrue("permission" in msg.lower() or "continue" in msg.lower())

        # Test rejected confirmation blocks execution
        denied_agent = NeoAgent(confirm_callback=lambda tool, args: False)
        succ, res = denied_agent.execute_action({"tool": "delete_path", "arguments": {"path": "safe_file.txt"}})
        self.assertFalse(succ)
        self.assertIn("cancelled", res.lower())

        print("  [PASS] Destructive operation confirmation enforcement verified.")

    # ============================================================
    # 4. OLLAMA RELIABILITY, OFFLINE FALLBACK & JSON RECOVERY
    # ============================================================

    def test_07_dynamic_model_discovery(self):
        """Verify dynamic local model discovery via Ollama."""
        models = llm_manager.list_models()
        self.assertIsInstance(models, list)
        if models:
            print(f"  [PASS] Discovered {len(models)} local Ollama model(s): {models[:3]}")
        else:
            print("  [PASS] Model discovery tested (Ollama offline or no local models).")

    def test_08_json_error_recovery(self):
        """Verify robust recovery from markdown fences, embedded JSON, and malformed outputs."""
        # 1. Clean JSON
        parsed1 = _extract_and_parse_json('{"type": "chat", "response": "Hello!"}')
        self.assertEqual(parsed1.get("type"), "chat")
        self.assertEqual(parsed1.get("response"), "Hello!")

        # 2. Markdown code fenced JSON
        fenced = "```json\n{\"type\": \"action\", \"actions\": [{\"tool\": \"screenshot\"}]}\n```"
        parsed2 = _extract_and_parse_json(fenced)
        self.assertEqual(parsed2.get("type"), "action")
        self.assertEqual(parsed2.get("actions")[0]["tool"], "screenshot")

        # 3. Unformatted conversational fallback
        plain = "Here is your requested answer without json."
        parsed3 = _extract_and_parse_json(plain)
        self.assertEqual(parsed3.get("type"), "chat")
        self.assertEqual(parsed3.get("response"), plain)

        print("  [PASS] JSON extraction and malformed response recovery validated.")

    def test_09_offline_rule_fallback_when_ollama_fails(self):
        """Verify agent handles Ollama outages gracefully without failing PC actions."""
        with patch("core.agent.ask_ollama", side_effect=OllamaError("Connection refused")):
            # Deterministic command should succeed completely without calling Ollama
            res1 = self.agent.run("tell me how much ram is available")
            self.assertIn("RAM", res1)

            res2 = self.agent.run("open the downloads folder")
            self.assertIn("Downloads", res2)

            # Unknown open-ended command should gracefully explain offline mode
            res3 = self.agent.run("what is quantum computing theory in 18th century")
            self.assertIn("NEO AI", res3)
            self.assertIn("Offline", res3)

        print("  [PASS] Offline rule-based fallback and graceful outage recovery verified.")

    # ============================================================
    # 5. CONTEXT MANAGEMENT & OPERATION CANCELLATION
    # ============================================================

    def test_10_conversation_history_pruning_and_clearing(self):
        """Verify conversation history pruning and memory clearing."""
        agent = NeoAgent()
        agent.clear_conversation()
        self.assertEqual(len(agent.conversation), 0)

        # Record multiple turns
        for i in range(12):
            agent._record_conversation(f"User message {i}", f"Assistant answer {i}")

        # Configured max turns is 8 (16 messages)
        self.assertLessEqual(len(agent.conversation), 16)

        # Clear conversation
        clear_res = agent.clear_conversation()
        self.assertEqual(len(agent.conversation), 0)
        self.assertIn("cleared", clear_res.lower())
        print("  [PASS] Conversation sliding window and context clearing verified.")

    def test_11_cancellation_of_active_operations(self):
        """Verify cancellation stops active execution."""
        agent = NeoAgent()
        agent.cancel_current_operation()
        self.assertTrue(agent.is_cancelled)

        # Executing an action while cancelled returns cancelled result
        succ, res = agent.execute_action({"tool": "screenshot", "arguments": {}})
        self.assertFalse(succ)
        self.assertIn("cancelled", res.lower())

        print("  [PASS] Active operation cancellation verified.")


if __name__ == "__main__":
    unittest.main()
