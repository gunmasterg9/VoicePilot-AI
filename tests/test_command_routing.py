"""
NEO AI - Command Routing & Dispatch Unit Tests
Verifies deterministic voice and text command routing, wake word stripping,
Windows action safety, Recycle Bin shell execution, browser tab handling,
local file search vs web search separation, and telemetry boundary isolation.
All OS actions are mocked so no applications or windows are opened during tests.
"""

import sys
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.agent import NeoAgent
from core.router import route_direct_command


class TestCommandRouting(unittest.TestCase):
    """Test suite for voice and text command routing."""

    def setUp(self):
        self.agent = NeoAgent()

    # ============================================================
    # 1. RECYCLE BIN
    # ============================================================

    @patch("subprocess.Popen")
    @patch("webbrowser.open")
    def test_open_recycle_bin_direct(self, mock_web_open, mock_popen):
        """'Open Recycle Bin' must open Windows Recycle Bin folder and never a browser."""
        response = self.agent.run("Open Recycle Bin")
        self.assertIsNotNone(response)
        self.assertIn("recycle bin", response.lower())

        # Verify subprocess was called with explorer.exe shell:RecycleBinFolder
        mock_popen.assert_called()
        args = mock_popen.call_args[0][0]
        self.assertIn("explorer.exe", args[0].lower())
        self.assertIn("shell:recyclebinfolder", [a.lower() for a in args])

        # Verify browser was NEVER opened
        mock_web_open.assert_not_called()

    @patch("subprocess.Popen")
    @patch("webbrowser.open")
    def test_hello_neo_open_recycle_bin(self, mock_web_open, mock_popen):
        """'Hello NEO, open Recycle Bin' must strip wake phrase, open Recycle Bin, and never open browser."""
        response = self.agent.run("Hello NEO, open Recycle Bin")
        self.assertIsNotNone(response)
        self.assertIn("recycle bin", response.lower())

        mock_popen.assert_called()
        args = mock_popen.call_args[0][0]
        self.assertIn("explorer.exe", args[0].lower())
        self.assertIn("shell:recyclebinfolder", [a.lower() for a in args])

        mock_web_open.assert_not_called()

    # ============================================================
    # 2. OPEN NEW TAB
    # ============================================================

    @patch("webbrowser.open_new_tab")
    @patch("pygetwindow.getAllWindows", return_value=[])
    def test_open_new_tab_fallback(self, mock_windows, mock_open_tab):
        """'Open new tab' when no browser window is open should use safe fallback and not Notepad."""
        response = self.agent.run("Open new tab")
        self.assertIsNotNone(response)
        self.assertNotIn("notepad", response.lower())
        self.assertTrue("browser" in response.lower() or "tab" in response.lower())
        mock_open_tab.assert_called_once()

    @patch("pyautogui.hotkey")
    @patch("pygetwindow.getAllWindows")
    def test_open_new_tab_with_existing_browser(self, mock_windows, mock_hotkey):
        """'Open new tab' when browser window is present activates browser and sends Ctrl+T."""
        mock_win = MagicMock()
        mock_win.title = "Google Chrome - New Tab"
        mock_windows.return_value = [mock_win]

        response = self.agent.run("Open new tab")
        self.assertIsNotNone(response)
        self.assertNotIn("notepad", response.lower())
        mock_win.activate.assert_called_once()
        mock_hotkey.assert_called_once_with("ctrl", "t")

    @patch("webbrowser.open_new_tab")
    @patch("pygetwindow.getAllWindows", return_value=[])
    def test_neo_open_a_new_tab_wake_phrase(self, mock_windows, mock_open_tab):
        """'NEO, open a new tab' must strip wake phrase, trigger new tab, and never open Notepad."""
        response = self.agent.run("NEO, open a new tab")
        self.assertIsNotNone(response)
        self.assertNotIn("notepad", response.lower())
        mock_open_tab.assert_called_once()

    # ============================================================
    # 3. SEARCH MY PC VS WEB SEARCH
    # ============================================================

    @patch("subprocess.Popen")
    @patch("webbrowser.open")
    def test_search_my_pc(self, mock_web_open, mock_popen):
        """'Search my PC' must open Windows Search and never launch Google."""
        response = self.agent.run("Search my PC")
        self.assertIsNotNone(response)
        self.assertIn("windows search", response.lower())

        mock_popen.assert_called()
        args = mock_popen.call_args[0][0]
        self.assertIn("explorer.exe", args[0].lower())
        self.assertTrue(any("search-ms:" in a.lower() for a in args))
        mock_web_open.assert_not_called()

    @patch("subprocess.Popen")
    @patch("webbrowser.open")
    def test_find_files_on_my_computer(self, mock_web_open, mock_popen):
        """'Find files on my computer' must trigger local search, not web search."""
        response = self.agent.run("Find files on my computer")
        self.assertIsNotNone(response)
        self.assertIn("windows search", response.lower())

        mock_popen.assert_called()
        mock_web_open.assert_not_called()

    @patch("subprocess.Popen")
    @patch("webbrowser.open")
    def test_search_files_on_my_pc(self, mock_web_open, mock_popen):
        """'Search files on my PC' must trigger local search, not Google."""
        response = self.agent.run("Search files on my PC")
        self.assertIsNotNone(response)
        self.assertIn("windows search", response.lower())

        mock_popen.assert_called()
        mock_web_open.assert_not_called()

    @patch("webbrowser.open")
    @patch("subprocess.Popen")
    def test_search_google_for_my_pc(self, mock_popen, mock_web_open):
        """'Search Google for my PC' must perform web search with URL-encoded query."""
        response = self.agent.run("Search Google for my PC")
        self.assertIsNotNone(response)
        self.assertIn("searching google", response.lower())

        mock_web_open.assert_called()
        opened_url = mock_web_open.call_args[0][0]
        self.assertIn("google.com/search?q=", opened_url)
        self.assertIn("my+pc", opened_url.lower())
        mock_popen.assert_not_called()

    @patch("webbrowser.open")
    def test_search_the_web_for_my_pc(self, mock_web_open):
        """'Search the web for my PC' must route to web search."""
        response = self.agent.run("Search the web for my PC")
        self.assertIsNotNone(response)
        self.assertTrue("searching google" in response.lower() or "searching the web" in response.lower())

        mock_web_open.assert_called()
        opened_url = mock_web_open.call_args[0][0]
        self.assertIn("google.com/search?q=", opened_url)
        self.assertIn("my+pc", opened_url.lower())

    # ============================================================
    # 4. PRESERVED WORKING COMMANDS
    # ============================================================

    def test_what_time_is_it_local_datetime(self):
        """'What time is it?' must be handled locally using Python datetime."""
        response = self.agent.run("What time is it?")
        self.assertIsNotNone(response)
        now = datetime.now()
        expected_am_pm = now.strftime("%p")
        self.assertIn("current time is", response.lower())
        self.assertIn(expected_am_pm.lower(), response.lower())

    def test_hello_neo_what_time_is_it(self):
        """'Hello NEO, what time is it?' must strip wake phrase and handle via datetime."""
        response = self.agent.run("Hello NEO, what time is it?")
        self.assertIsNotNone(response)
        self.assertIn("current time is", response.lower())

    def test_what_is_todays_date_local_datetime(self):
        """'What is today's date?' must be handled locally using Python datetime."""
        response = self.agent.run("What is today's date?")
        self.assertIsNotNone(response)
        now = datetime.now()
        expected_year = str(now.year)
        self.assertIn("today is", response.lower())
        self.assertIn(expected_year, response)

    def test_hello_neo_what_is_todays_date(self):
        """'Hello NEO, what is today's date?' must strip wake phrase and handle via datetime."""
        response = self.agent.run("Hello NEO, what is today's date?")
        self.assertIsNotNone(response)
        now = datetime.now()
        expected_year = str(now.year)
        self.assertIn("today is", response.lower())
        self.assertIn(expected_year, response)

    @patch("subprocess.Popen")
    def test_open_notepad(self, mock_popen):
        """'Open Notepad' must open Notepad deterministically."""
        response = self.agent.run("Open Notepad")
        self.assertIsNotNone(response)
        self.assertIn("notepad", response.lower())
        mock_popen.assert_called()
        args = mock_popen.call_args[0][0]
        self.assertIn("notepad.exe", args[0].lower())

    @patch("subprocess.Popen")
    def test_hello_neo_open_notepad(self, mock_popen):
        """'Hello NEO, open Notepad' must strip wake phrase and open Notepad deterministically."""
        response = self.agent.run("Hello NEO, open Notepad")
        self.assertIsNotNone(response)
        self.assertIn("notepad", response.lower())
        mock_popen.assert_called()
        args = mock_popen.call_args[0][0]
        self.assertIn("notepad.exe", args[0].lower())

    def test_who_are_you_identity(self):
        """'Who are you?' must return NEO identity without calling LLM."""
        response = self.agent.run("Who are you?")
        self.assertIsNotNone(response)
        self.assertIn("neo", response.lower())
        self.assertIn("local ai pc assistant", response.lower())

    # ============================================================
    # 5. TELEMETRY BOUNDARY & UNRELATED QUESTION ISOLATION
    # ============================================================

    @patch("core.agent.ask_ollama")
    def test_unrelated_ordinary_questions_do_not_trigger_telemetry(self, mock_ask_ollama):
        """Unrelated questions containing keywords like battery, memory, cpu must NOT trigger telemetry."""
        mock_ask_ollama.return_value = {
            "type": "chat",
            "response": "General conversational answer.",
            "actions": []
        }

        unrelated_questions = [
            "What is a car battery?",
            "How does a battery work?",
            "What is the battery life of an iPhone 15?",
            "How much memory does a human brain have?",
            "What is a CPU cache?",
            "What is the system status of the Apollo mission?",
            "Explain quantum computing theory",
            "Tell me about the Roman Empire",
        ]

        for q in unrelated_questions:
            with self.subTest(question=q):
                # Verify deterministic router does NOT classify as telemetry
                routed = route_direct_command(q)
                if routed:
                    actions = routed.get("actions", [])
                    tools_called = [a.get("tool") for a in actions]
                    self.assertNotIn("get_system_telemetry", tools_called, f"'{q}' triggered get_system_telemetry in router")
                    self.assertNotIn("get_ram_info", tools_called, f"'{q}' triggered get_ram_info in router")

                # Verify agent run does NOT return hardware metrics
                response = self.agent.run(q)
                self.assertIsNotNone(response)
                self.assertNotIn("system telemetry: battery is at", response.lower(), f"'{q}' triggered battery telemetry")
                self.assertNotIn("current cpu usage is", response.lower(), f"'{q}' triggered CPU telemetry")
                self.assertNotIn("ram usage is", response.lower(), f"'{q}' triggered RAM telemetry")

    def test_explicit_telemetry_requests_still_work(self):
        """Explicit hardware telemetry commands must return metrics."""
        explicit_telemetry_commands = [
            ("check cpu usage", "cpu"),
            ("how much memory is used", "ram"),
            ("tell me how much ram is available", "ram"),
            ("check battery and system status", "system telemetry"),
        ]

        for cmd, expected_keyword in explicit_telemetry_commands:
            with self.subTest(command=cmd):
                response = self.agent.run(cmd)
                self.assertIsNotNone(response)
                self.assertIn(expected_keyword, response.lower())


if __name__ == "__main__":
    unittest.main()
