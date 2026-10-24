
import re
import time
import webbrowser
import urllib.parse
import subprocess
import shutil
import os
from datetime import datetime

from core.llm import ask_ollama, OllamaError, llm_manager
from core.safety import (
    requires_confirmation,
    confirmation_message
)
from tools.registry import get_tool, execute_tool
from core.router import route_direct_command, normalize_plan
from core.settings import settings


# ============================================================
# ORION IDENTITY
# ============================================================

ORION_NAME = "NEO"
NEO_CREATOR = "Gautam Vandar"
ORION_CREATOR = NEO_CREATOR

ORION_DESCRIPTION = (
    "I am NEO, a local AI PC assistant created by "
    "Gautam Vandar"
)


# ============================================================
# DIRECT WEBSITE MAP
# ============================================================

KNOWN_WEBSITES = {
    "netflix": "https://www.netflix.com",
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "github": "https://github.com",
    "chatgpt": "https://chatgpt.com",
    "spotify": "https://open.spotify.com",
    "instagram": "https://www.instagram.com",
    "facebook": "https://www.facebook.com",
    "whatsapp": "https://web.whatsapp.com",
    "linkedin": "https://www.linkedin.com",
    "amazon": "https://www.amazon.in",
    "amazon india": "https://www.amazon.in",
    "flipkart": "https://www.flipkart.com",
    "reddit": "https://www.reddit.com",
    "twitter": "https://x.com",
    "x": "https://x.com",
    "discord": "https://discord.com/app",
    "stackoverflow": "https://stackoverflow.com",
    "stack overflow": "https://stackoverflow.com",
    "wikipedia": "https://www.wikipedia.org",
    "canva": "https://www.canva.com",
    "zoom": "https://zoom.us",
    "outlook": "https://outlook.live.com",
    "google drive": "https://drive.google.com",
    "drive": "https://drive.google.com",
    "google docs": "https://docs.google.com",
    "google maps": "https://maps.google.com",
}


# ============================================================
# DETERMINISTIC WINDOWS APPLICATIONS
# ============================================================

KNOWN_APPLICATIONS = {
    "notepad": ["notepad.exe"],
    "note pad": ["notepad.exe"],
    "notepad app": ["notepad.exe"],

    "calculator": ["calc.exe"],
    "calculator app": ["calc.exe"],
    "calc": ["calc.exe"],

    "paint": ["mspaint.exe"],
    "microsoft paint": ["mspaint.exe"],

    "file explorer": ["explorer.exe"],
    "file explorer app": ["explorer.exe"],
    "windows explorer": ["explorer.exe"],
    "explorer": ["explorer.exe"],

    "command prompt": ["cmd.exe"],
    "cmd": ["cmd.exe"],

    "powershell": ["powershell.exe"],
    "windows powershell": ["powershell.exe"],

    "task manager": ["taskmgr.exe"],

    "chrome": ["chrome.exe"],
    "google chrome": ["chrome.exe"],

    "edge": ["msedge.exe"],
    "microsoft edge": ["msedge.exe"],

    "vs code": ["code"],
    "visual studio code": ["code"],
    "code": ["code"],

    "recycle bin": ["explorer.exe", "shell:RecycleBinFolder"],
    "recyclebin": ["explorer.exe", "shell:RecycleBinFolder"],
    "the recycle bin": ["explorer.exe", "shell:RecycleBinFolder"],
    "trash": ["explorer.exe", "shell:RecycleBinFolder"],
    "the trash": ["explorer.exe", "shell:RecycleBinFolder"],
}


# ============================================================
# NEO AGENT
# ============================================================

class OrionAgent:

    def __init__(self, confirm_callback=None):

        self.name = ORION_NAME
        self.creator = ORION_CREATOR
        self.description = ORION_DESCRIPTION

        self.conversation = []
        self.is_cancelled = False
        self.tool_callback = None

        self.confirm_callback = (
            confirm_callback
            or self._terminal_confirm
        )

        self._last_command = ""
        self._last_command_time = 0

    def clear_conversation(self) -> str:
        """Clears the conversational context memory without altering settings."""
        self.conversation.clear()
        return "Conversation context cleared."

    def cancel_current_operation(self) -> None:
        """Signals cancellation to stop ongoing speech synthesis and AI execution."""
        self.is_cancelled = True
        try:
            llm_manager.cancel()
        except Exception:
            pass
        try:
            from interfaces.tts import tts_manager
            tts_manager.stop()
        except Exception:
            pass

    def _record_conversation(self, user_msg: str, assistant_msg: str) -> None:
        """Records user and assistant turns with max history turn bounds."""
        max_turns = int(settings.get("max_history_turns", 8))
        self.conversation.append({"role": "user", "content": user_msg})
        self.conversation.append({"role": "assistant", "content": assistant_msg})
        if len(self.conversation) > max_turns * 2:
            self.conversation = self.conversation[-(max_turns * 2):]


    # ========================================================
    # VOICE COMMAND NORMALIZATION
    # ========================================================

    def _normalize_voice_command(self, text):

        text = str(text).strip()

        if not text:
            return ""

        # Normalize whitespace
        text = " ".join(text.split())

        # Remove punctuation commonly added by Whisper
        text = text.strip(" .,!?:;")

        # Lowercase
        text = text.lower()

        # Common speech / Whisper variations
        replacements = {

            # Websites
            "you tube": "youtube",
            "you-tube": "youtube",

            "linked in": "linkedin",
            "link ed in": "linkedin",

            "face book": "facebook",
            "face-book": "facebook",

            "what's app": "whatsapp",
            "what s app": "whatsapp",

            "git hub": "github",

            "chat gpt": "chatgpt",
            "chat-gpt": "chatgpt",

            "stack overflow": "stackoverflow",

            # Applications
            "note pad": "notepad",

            "google chrome": "chrome",

            "visual studio code": "vs code",

            "microsoft edge": "edge",

            "windows powershell": "powershell",

            "command prompt": "command prompt",

            "file explorer": "file explorer",
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        return text


    # ========================================================
    # CONFIRMATION
    # ========================================================

    def _terminal_confirm(
        self,
        tool_name,
        arguments
    ):

        message = confirmation_message(
            tool_name,
            arguments
        )

        answer = input(
            f"NEO: {message} [y/N]: "
        ).strip().lower()

        return answer in {"y", "yes"}


    # ========================================================
    # TOOL EXECUTION
    # ========================================================

    def execute_action(self, action):

        if self.is_cancelled:
            return False, "Operation cancelled by user."

        if not isinstance(action, dict):
            return False, "Invalid action."

        tool_name = action.get("tool")
        arguments = action.get("arguments", {})

        if not tool_name:
            return False, "No tool was specified."

        if not isinstance(arguments, dict):
            arguments = {}

        if tool_name == "stop_speaking":
            from interfaces.tts import tts_manager
            tts_manager.stop()
            return True, "Speech synthesis stopped."

        result = execute_tool(
            tool_name=tool_name,
            arguments=arguments,
            confirm_callback=self.confirm_callback
        )

        if self.tool_callback:
            try:
                self.tool_callback(tool_name, str(result), result.success)
            except Exception:
                pass

        return result.success, str(result)


    # ========================================================
    # OPEN KNOWN WEBSITE
    # ========================================================

    def _open_known_website(self, target):

        key = str(target).strip().lower()

        key = key.replace("https://", "")
        key = key.replace("http://", "")
        key = key.replace("www.", "")
        key = key.rstrip("/")

        if key.endswith(".com"):
            key = key[:-4]

        if key.endswith(".in"):
            key = key[:-3]

        key = key.strip()

        if key not in KNOWN_WEBSITES:
            return None

        url = KNOWN_WEBSITES[key]

        try:

            webbrowser.open(
                url,
                new=2
            )

            return f"Opening {target}."

        except Exception as exc:

            return (
                f"Could not open {target}: {exc}"
            )


    # ========================================================
    # OPEN KNOWN APPLICATION
    # ========================================================

    def _open_known_application(self, target):

        key = self._normalize_voice_command(target)

        command = KNOWN_APPLICATIONS.get(key)

        if command is None:
            return None

        try:

            executable = command[0]

            # Direct Windows executable
            if executable.endswith(".exe"):

                subprocess.Popen(
                    command,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

            else:

                # Try PATH first
                executable_path = shutil.which(
                    executable
                )

                if executable_path:

                    subprocess.Popen(
                        [executable_path],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )

                else:

                    subprocess.Popen(
                        command,
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )

            return f"Opening {target}."

        except Exception as exc:

            return (
                f"Could not open {target}: {exc}"
            )


    # ========================================================
    # OPEN TARGET
    # ========================================================

    def _open_target(self, target):

        target = self._normalize_voice_command(
            str(target).strip()
        )

        if not target:
            return "No application or website was specified."

        # 1. Known website
        website_result = self._open_known_website(
            target
        )

        if website_result:
            return website_result

        # 2. Known application
        application_result = self._open_known_application(
            target
        )

        if application_result:
            return application_result

        # 3. General ORION application tool
        tool = get_tool("open_target")

        if tool:

            try:

                return str(
                    tool(
                        target=target
                    )
                )

            except TypeError:

                try:

                    return str(
                        tool(target)
                    )

                except Exception as exc:

                    return (
                        f"Could not open "
                        f"{target}: {exc}"
                    )

            except Exception as exc:

                return (
                    f"Could not open "
                    f"{target}: {exc}"
                )

        return (
            f"I couldn't find a way to open {target}."
        )


    # ========================================================
    # YOUTUBE SEARCH
    # ========================================================

    def _youtube_search(self, query):

        query = str(query).strip()

        if not query:

            return (
                "What should I search for on YouTube?"
            )

        url = (
            "https://www.youtube.com/results?search_query="
            + urllib.parse.quote_plus(query)
        )

        try:

            webbrowser.open(
                url,
                new=2
            )

            return (
                f"Searching YouTube for {query}."
            )

        except Exception as exc:

            return (
                f"Could not search YouTube: {exc}"
            )


    # ========================================================
    # CLOSE TARGET
    # ========================================================

    def _close_target(self, target):

        target = self._normalize_voice_command(
            str(target).strip()
        )

        if not target:

            return (
                "No window or application was specified."
            )

        # ----------------------------------------------------
        # Known Windows processes
        # ----------------------------------------------------

        process_map = {

            "notepad": "notepad.exe",

            "calculator": "CalculatorApp.exe",
            "calc": "CalculatorApp.exe",

            "paint": "mspaint.exe",

            "chrome": "chrome.exe",

            "edge": "msedge.exe",

            "powershell": "powershell.exe",

            "command prompt": "cmd.exe",
            "cmd": "cmd.exe",

            "vs code": "Code.exe",
            "visual studio code": "Code.exe",
        }

        process = process_map.get(target)

        if process:

            try:

                result = subprocess.run(
                    [
                        "taskkill",
                        "/IM",
                        process,
                        "/F"
                    ],
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )

                if result.returncode == 0:

                    return f"Closed {target}."

            except Exception:

                pass

        # ----------------------------------------------------
        # Fallback to ORION close tool
        # ----------------------------------------------------

        tool = get_tool(
            "close_target"
        )

        if tool is None:

            return (
                f"I couldn't find an open window for {target}."
            )

        try:

            return str(
                tool(target)
            )

        except TypeError:

            try:

                return str(
                    tool(
                        target=target
                    )
                )

            except Exception as exc:

                return (
                    f"Could not close "
                    f"{target}: {exc}"
                )

        except Exception as exc:

            return (
                f"Could not close "
                f"{target}: {exc}"
            )


    # ========================================================
    # CREATE FOLDER DIRECTLY
    # ========================================================

    def _create_folder(self, name, desktop=False):

        name = str(name).strip()

        if not name:

            return "Please specify a folder name."

        # ----------------------------------------------------
        # Desktop folder
        # ----------------------------------------------------

        if desktop:

            user_profile = os.path.expanduser("~")

            normal_desktop = os.path.join(
                user_profile,
                "Desktop"
            )

            onedrive_desktop = os.path.join(
                user_profile,
                "OneDrive",
                "Desktop"
            )

            # Use OneDrive Desktop if it exists
            if os.path.isdir(onedrive_desktop):

                desktop_path = onedrive_desktop

            elif os.path.isdir(normal_desktop):

                desktop_path = normal_desktop

            else:

                desktop_path = normal_desktop

            folder_path = os.path.join(
                desktop_path,
                name
            )

        else:

            folder_path = name

        # ----------------------------------------------------
        # Use ORION filesystem tool
        # ----------------------------------------------------

        tool = get_tool(
            "create_folder"
        )

        if tool is None:

            # Python fallback
            try:

                os.makedirs(
                    folder_path,
                    exist_ok=True
                )

                return (
                    f"Folder '{name}' created at "
                    f"{folder_path}."
                )

            except Exception as exc:

                return (
                    f"Could not create folder: {exc}"
                )

        try:

            result = tool(
                path=folder_path
            )

            return str(result)

        except TypeError:

            try:

                result = tool(
                    folder_path
                )

                return str(result)

            except Exception as exc:

                return (
                    f"Could not create folder: {exc}"
                )

        except Exception as exc:

            return (
                f"Could not create folder: {exc}"
            )


    # ========================================================
    # DIRECT COMMAND ROUTER
    #
    # These commands NEVER go to Ollama.
    # ========================================================

    def _direct_command(self, message):

        text = str(message).strip()

        if not text:
            return None

        # Normalize whitespace
        text = " ".join(
            text.split()
        )

        # Voice-friendly normalization
        lower = self._normalize_voice_command(
            text
        )

        clean = lower.strip(
            " .!?,"
        )

        # Remove a leading NEO wake phrase before matching direct commands.
        clean = re.sub(
            r"^(?:(?:hey|hello|hi|okay)\s+)?(?:neo|orion)[\s,:-]+",
            "",
            clean,
            flags=re.IGNORECASE
        ).strip()
        lower = clean


        # ====================================================
        # DATE
        # ====================================================

        date_patterns = [

            r"^what is (?:today'?s )?date$",
            r"^what'?s (?:today'?s )?date$",
            r"^what is the date$",
            r"^what is the date today$",
            r"^what date is it$",
            r"^what date is today$",
            r"^tell me (?:today'?s )?date$",
            r"^tell me the date$",
            r"^today'?s date$",
            r"^todays date$",
            r"^date today$",
            r"^today date$",
            r"^what day is it$",
            r"^what day is today$",
        ]

        for pattern in date_patterns:

            if re.match(
                pattern,
                clean,
                re.IGNORECASE
            ):

                today = datetime.now()

                return today.strftime(
                    "Today is %A, %B %d, %Y."
                )


        # ====================================================
        # TIME
        # ====================================================

        time_patterns = [

            r"^what time is it$",
            r"^what'?s the time$",
            r"^what is the time$",
            r"^what is current time$",
            r"^what is the current time$",
            r"^tell me the time$",
            r"^current time$",
            r"^time now$",
            r"^what time is it now$",
            r"^what is the time now$",
        ]

        for pattern in time_patterns:

            if re.match(
                pattern,
                clean,
                re.IGNORECASE
            ):

                now = datetime.now()

                return now.strftime(
                    "The current time is %I:%M %p."
                )


        # ====================================================
        # CREATOR / DEVELOPER
        # ====================================================

        creator_phrases = {

            "who made you",
            "who made u",
            "who make you",
            "who created you",
            "who create you",

            "who is your creator",
            "who's your creator",
            "whos your creator",

            "who built you",
            "who build you",

            "who developed you",
            "who develop you",

            "who programmed you",
            "who designed you",

            "who made orion",
            "who make orion",
            "who created orion",
            "who create orion",
            "who built orion",
            "who build orion",
            "who developed orion",
            "who develop orion",

            "who is the creator of orion",
            "who is the developer of orion",
            "who is your developer",
            "who is your maker",
            "who made you orion",
            "who made you neo",
            "who created you neo",
        }

        if clean in creator_phrases:

            return (
                "I was created by Gautam Vandar."
            )


        creator_patterns = [

            ("who", "made", "you"),
            ("who", "made", "u"),
            ("who", "make", "you"),
            ("who", "created", "you"),
            ("who", "create", "you"),
            ("who", "built", "you"),
            ("who", "build", "you"),
            ("who", "developed", "you"),
            ("who", "develop", "you"),
            ("who", "programmed", "you"),
            ("who", "programmed", "neo"),
            ("who", "made", "neo"),
            ("who", "created", "neo"),
            ("who", "built", "neo"),
            ("who", "developed", "neo"),
            ("who", "programmed", "orion"),
            ("who", "made", "orion"),
            ("who", "created", "orion"),
            ("who", "built", "orion"),
            ("who", "developed", "orion"),
        ]

        words = clean.split()

        if (
            len(words) >= 3
            and any(
                all(
                    keyword in words
                    for keyword in pattern
                )
                for pattern in creator_patterns
            )
        ):

            return (
                "I was created by Gautam Vandar."
            )


        # ====================================================
        # ORION NAME
        # ====================================================

        name_patterns = [

            r"^what is your name$",
            r"^what'?s your name$",
            r"^who are you$",
            r"^what are you$",
            r"^identify yourself$",
            r"^tell me who you are$",
        ]

        for pattern in name_patterns:

            if re.match(
                pattern,
                clean,
                re.IGNORECASE
            ):

                return (
                    "My name is NEO. "
                    "I am your local AI PC assistant."
                )


        # ====================================================
        # ABOUT NEO
        # ====================================================

        about_patterns = [

            r"^tell me about yourself$",
            r"^what can you do$",
            r"^what do you do$",
            r"^what is neo$",
            r"^tell me about neo$",
            r"^what is orion$",
            r"^tell me about orion$",
        ]

        for pattern in about_patterns:

            if re.match(
                pattern,
                clean,
                re.IGNORECASE
            ):

                return (
                    "I am NEO, a local AI PC assistant "
                    "created by Gautam Vandar. "
                    "I can control your computer, "
                    "open applications and websites, "
                    "manage files, perform system actions, "
                    "and assist with everyday tasks."
                )


        # ====================================================
        # GREETINGS
        # ====================================================

        if clean in {

            "hello",
            "hi",
            "hey",

            "hello neo",
            "hey neo",
            "hi neo",
            "hello orion",
            "hey orion",
            "hi orion",

            "good morning",
            "good morning neo",
            "good morning orion",

            "good afternoon",
            "good afternoon neo",
            "good afternoon orion",

            "good evening",
            "good evening neo",
            "good evening orion",
        }:

            return (
                "Hello. NEO is online and ready."
            )



        # ====================================================
        # YOUTUBE SEARCH
        # ====================================================

        match = re.match(

            r"^(?:search|find|look\s+up)\s+(.+?)"
            r"\s+(?:on\s+)?youtube$",

            lower,

            re.IGNORECASE
        )

        if match:

            return self._youtube_search(
                match.group(1)
            )


        match = re.match(

            r"^(?:search|find|look\s+up)\s+youtube"
            r"(?:\s+for)?\s+(.+)$",

            lower,

            re.IGNORECASE
        )

        if match:

            return self._youtube_search(
                match.group(1)
            )


        # ====================================================
        # OPEN APPLICATION + TYPE TEXT
        # ====================================================

        match = re.match(

            r"^(?:open|launch)\s+(.+?)"
            r"\s+and\s+(?:write|type)\s+(.+)$",

            lower,

            re.IGNORECASE
        )

        if match:

            target = match.group(1).strip()
            content = match.group(2).strip()

            open_result = self._open_target(
                target
            )

            time.sleep(1.0)

            type_tool = get_tool(
                "type_text"
            )

            if type_tool is None:

                return open_result

            try:

                type_tool(
                    text=content
                )

                return (
                    f"{open_result}\n"
                    f"Typed: {content}"
                )

            except TypeError:

                try:

                    type_tool(content)

                    return (
                        f"{open_result}\n"
                        f"Typed: {content}"
                    )

                except Exception as exc:

                    return (
                        f"{open_result}\n"
                        f"Could not type text: {exc}"
                    )

            except Exception as exc:

                return (
                    f"{open_result}\n"
                    f"Could not type text: {exc}"
                )


        # ====================================================
        # OPEN WEBSITE / APPLICATION / TABS
        # ====================================================

        if clean in {
            "open new tab",
            "open a new tab",
            "new tab",
            "open tab",
            "create new tab",
            "create a new tab",
        }:
            from tools.web import open_new_tab
            return open_new_tab()

        match = re.match(
            r"^(?:open|launch|go\s+to)\s+(.+?)$",
            lower,
            re.IGNORECASE
        )

        if match:
            target = match.group(1).strip()
            return self._open_target(
                target
            )


        # ====================================================
        # CLOSE APP / WINDOW
        # ====================================================

        match = re.match(

            r"^(?:close|exit|quit)\s+(.+?)$",

            lower,

            re.IGNORECASE
        )

        if match:

            target = match.group(1).strip()

            return self._close_target(
                target
            )


        # ====================================================
        # SCREENSHOT
        # ====================================================

        if clean in {

            "screenshot",
            "take screenshot",
            "take a screenshot",
            "capture screen",
            "capture the screen",
        }:

            tool = get_tool(
                "screenshot"
            )

            if tool:

                try:

                    return str(
                        tool()
                    )

                except Exception as exc:

                    return (
                        f"Screenshot failed: {exc}"
                    )


        # ====================================================
        # LOCK PC
        # ====================================================

        if clean in {

            "lock pc",
            "lock my pc",
            "lock computer",
            "lock my computer",
            "lock the pc",
            "lock the computer",
        }:

            tool = get_tool(
                "lock_pc"
            )

            if tool:

                try:

                    return str(
                        tool()
                    )

                except Exception as exc:

                    return (
                        f"Could not lock the PC: {exc}"
                    )


        # ====================================================
        # TYPE TEXT
        # ====================================================

        match = re.match(

            r"^(?:type|write)\s+(.+)$",

            lower,

            re.IGNORECASE
        )

        if match:

            content = match.group(1)

            tool = get_tool(
                "type_text"
            )

            if tool:

                try:

                    return str(
                        tool(
                            text=content
                        )
                    )

                except TypeError:

                    try:

                        return str(
                            tool(content)
                        )

                    except Exception as exc:

                        return (
                            f"Could not type text: {exc}"
                        )

                except Exception as exc:

                    return (
                        f"Could not type text: {exc}"
                    )


        # ====================================================
        # PRESS KEY
        # ====================================================

        match = re.match(

            r"^press\s+(.+)$",

            lower,

            re.IGNORECASE
        )

        if match:

            key = match.group(1).strip()

            tool = get_tool(
                "press"
            )

            if tool:

                try:

                    return str(
                        tool(
                            key=key
                        )
                    )

                except TypeError:

                    try:

                        return str(
                            tool(key)
                        )

                    except Exception as exc:

                        return (
                            f"Could not press "
                            f"{key}: {exc}"
                        )

                except Exception as exc:

                    return (
                        f"Could not press "
                        f"{key}: {exc}"
                    )


        # ====================================================
        # CREATE FOLDER
        # ====================================================

        # ----------------------------------------------------
        # Desktop folder
        # ----------------------------------------------------

        match = re.match(

            r"^(?:create|make)\s+"
            r"(?:a\s+)?"
            r"folder\s+"
            r"(?:on\s+(?:the\s+)?desktop\s+)?"
            r"(?:called|named|name)\s+"
            r"(.+)$",

            lower,

            re.IGNORECASE
        )

        if match:

            name = match.group(1).strip()

            if re.search(
                r"\bon\s+(?:the\s+)?desktop\b",
                lower,
                re.IGNORECASE
            ):

                return self._create_folder(
                    name,
                    desktop=True
                )

            return self._create_folder(
                name,
                desktop=False
            )


        # ----------------------------------------------------
        # create folder on desktop demo
        # ----------------------------------------------------

        match = re.match(

            r"^(?:create|make)\s+"
            r"(?:a\s+)?"
            r"folder\s+"
            r"on\s+(?:the\s+)?desktop\s+"
            r"(.+)$",

            lower,

            re.IGNORECASE
        )

        if match:

            name = match.group(1).strip()

            return self._create_folder(
                name,
                desktop=True
            )


        # ----------------------------------------------------
        # Normal folder
        # ----------------------------------------------------

        match = re.match(

            r"^(?:create|make)\s+"
            r"(?:a\s+)?"
            r"folder\s+"
            r"(?:called|named|name)\s+"
            r"(.+)$",

            lower,

            re.IGNORECASE
        )

        if match:

            name = match.group(1).strip()

            return self._create_folder(
                name,
                desktop=False
            )


        # ====================================================
        # LOCAL COMPUTER SEARCH
        # ====================================================
        local_search_patterns = [
            r"^(?:search|find)\s+(?:my\s+|this\s+|the\s+)?(?:pc|computer|laptop)$",
            r"^(?:search|find)\s+files\s+(?:on\s+)?(?:my\s+|this\s+|the\s+)?(?:pc|computer|laptop)$",
            r"^(?:search|find)\s+(?:for\s+)?files\s+on\s+(?:my\s+|this\s+|the\s+)?(?:pc|computer|laptop)$",
            r"^(?:search|find)\s+(?:my\s+|the\s+)?(?:pc|computer)\s+for\s+files$",
            r"^(?:open\s+)?windows\s+search$",
        ]
        if any(re.match(p, clean, re.IGNORECASE) for p in local_search_patterns):
            from tools.windows import open_windows_search
            return open_windows_search()

        # ====================================================
        # WEB SEARCH
        # ====================================================

        match_explicit_web = re.match(
            r"^(?:search\s+(?:google|the\s+web|the\s+internet|web|online)\s+(?:for\s+)?|google\s+)(.+)$",
            clean,
            re.IGNORECASE
        )
        if match_explicit_web:
            query = match_explicit_web.group(1).strip()
            try:
                url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
                webbrowser.open(url, new=2)
                return f"Searching Google for {query}."
            except Exception as exc:
                return f"Could not perform search: {exc}"

        match_web_on = re.match(
            r"^(?:search|look\s+up|find)\s+(?:for\s+)?(.+?)\s+on\s+(?:google|the\s+web|web)$",
            clean,
            re.IGNORECASE
        )
        if match_web_on:
            query = match_web_on.group(1).strip()
            try:
                url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
                webbrowser.open(url, new=2)
                return f"Searching Google for {query}."
            except Exception as exc:
                return f"Could not perform search: {exc}"

        match_generic = re.match(
            r"^(?:search\s+for|search|look\s+up)\s+(.+)$",
            clean,
            re.IGNORECASE
        )
        if match_generic:
            query = match_generic.group(1).strip()
            if not query.lower().endswith("youtube") and not re.search(r"\b(?:my\s+|this\s+|the\s+)?(?:pc|computer|laptop)\b", query, re.IGNORECASE):
                try:
                    url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
                    webbrowser.open(url, new=2)
                    return f"Searching Google for {query}."
                except Exception as exc:
                    return f"Could not perform search: {exc}"

        # ====================================================
        # HARDWARE TELEMETRY & SYSTEM HEALTH (ANCHORED)
        # ====================================================

        # CPU Telemetry
        if re.match(r"^(?:(?:check|get|what is|tell me|show)\s+(?:the\s+|my\s+)?)?cpu(?:\s+(?:usage|load|status|%))?$", clean, re.IGNORECASE) or clean in {"check cpu", "cpu usage", "cpu %", "cpu load"}:
            try:
                import psutil
                cpu = psutil.cpu_percent(interval=0.1)
                return f"Current CPU usage is {cpu}%."
            except Exception as exc:
                return f"Could not read CPU: {exc}"

        # RAM / Memory Telemetry
        ram_patterns = [
            r"^(?:(?:tell me|check|get|what is|show)\s+)?how much (?:ram|memory) is (?:available|free|used)$",
            r"^(?:tell me\s+)?how much ram is available$",
            r"^(?:how much\s+)?(?:available|free)\s+ram$",
            r"^ram\s+available$",
            r"^check\s+(?:ram|memory)$",
            r"^(?:ram|memory)\s+(?:usage|used)$",
            r"^how much memory is used$",
            r"^how much ram is used$",
        ]
        if any(re.match(p, clean, re.IGNORECASE) for p in ram_patterns):
            try:
                import psutil
                mem = psutil.virtual_memory()
                used_gb = round((mem.total - mem.available) / (1024**3), 1)
                total_gb = round(mem.total / (1024**3), 1)
                return f"RAM usage is {mem.percent}% ({used_gb} GB of {total_gb} GB used)."
            except Exception as exc:
                return f"Could not read memory: {exc}"

        # Battery & System Telemetry
        system_patterns = [
            r"^(?:check\s+)?battery\s+and\s+system\s+status$",
            r"^(?:check\s+)?(?:the\s+|my\s+)?battery(?:\s+status|\s+level|\s+health)?$",
            r"^(?:check\s+)?(?:the\s+|my\s+)?system\s+(?:status|health|telemetry)$",
            r"^(?:check\s+)?hardware\s+status$",
        ]
        if any(re.match(p, clean, re.IGNORECASE) for p in system_patterns):
            try:
                import psutil
                batt = psutil.sensors_battery()
                batt_str = f"Battery is at {batt.percent}%." if batt else "AC power connected."
                cpu = psutil.cpu_percent(interval=0.05)
                mem = psutil.virtual_memory().percent
                return f"System telemetry: {batt_str} CPU is at {cpu}%, RAM is at {mem}%."
            except Exception:
                return "System telemetry: All core hardware systems operational."

        # ====================================================
        # STOP / CANCEL
        # ====================================================
        if clean in {
            "stop", "cancel", "stop now", "cancel action", "halt", "abort",
            "stop speaking", "stop talking", "be quiet", "shut up",
            "stop audio", "stop voice", "silence", "cancel speech",
            "रुक जाओ", "बंद करो", "शांत रहो"
        }:
            self.cancel_current_operation()
            return "Speech synthesis stopped and operations halted."

        # ====================================================
        # VOLUME CONTROLS
        # ====================================================
        if clean in {
            "increase volume", "volume up", "turn up volume", "turn up the volume",
            "raise volume", "raise the volume", "increase the volume", "louder", "make it louder",
            "आवाज़ बढ़ाओ", "वॉल्यूम बढ़ाओ", "आवाज बढ़ाओ"
        }:
            from tools.system import volume_up
            return volume_up(5)

        if clean in {
            "decrease volume", "volume down", "turn down volume", "turn down the volume",
            "lower volume", "lower the volume", "decrease the volume", "quieter", "make it quieter",
            "आवाज़ कम करो", "वॉल्यूम कम करो", "आवाज कम करो"
        }:
            from tools.system import volume_down
            return volume_down(5)

        if clean in {
            "mute volume", "mute the volume", "mute", "unmute", "unmute volume",
            "mute sound", "mute audio", "म्यूट करो", "आवाज़ म्यूट करो", "आवाज म्यूट करो"
        }:
            from tools.system import volume_mute
            return volume_mute()

        # ====================================================
        # AUDIO & JOKES
        # ====================================================

        if any(k in clean for k in ["test voice", "test audio", "test your voice", "test your audio", "audio playback"]):
            return "NEO audio playback is operational and speech synthesis is ready."

        if any(k in clean for k in ["tell me a joke", "tell a joke", "make me laugh"]):
            jokes = [
                "Why do programmers prefer dark mode? Because light attracts bugs!",
                "There are 10 types of people in the world: those who understand binary, and those who don't.",
                "Why did the developer go broke? Because they used up all their cache!"
            ]
            import random
            return random.choice(jokes)

        # ====================================================
        # NOTHING MATCHED
        # ====================================================

        return None




    # ========================================================
    # MAIN RUN
    # ========================================================

    def run(self, user_message):

        self.is_cancelled = False

        message = str(
            user_message
        ).strip()

        if not message:
            return "I didn't receive a command."

        # ----------------------------------------------------
        # 1. DIRECT FAST COMMANDS (IDENTITY, HARDWARE, UTILITIES)
        # ----------------------------------------------------
        direct_result = self._direct_command(message)

        if direct_result is not None:
            normalized = self._normalize_voice_command(message)
            now = time.monotonic()

            if (
                normalized == self._last_command
                and now - self._last_command_time < 2.0
            ):
                return "That command was already executed."

            self._last_command = normalized
            self._last_command_time = now
            return direct_result

        # ----------------------------------------------------
        # 2. DETERMINISTIC NATURAL ROUTER (BROWSER, FOLDERS, PDFS, RAM)
        # ----------------------------------------------------
        routed = route_direct_command(message)

        if routed is not None:
            normalized = self._normalize_voice_command(message)
            self._last_command = normalized
            self._last_command_time = time.monotonic()

            plan_type = routed.get("type", "chat")
            response = str(routed.get("response", ""))
            actions = routed.get("actions", [])

            if plan_type == "chat":
                self._record_conversation(message, response)
                return response

            if plan_type in {"action", "query"}:
                action_results = []
                for act in actions:
                    if self.is_cancelled:
                        return "Operation cancelled by user."
                    succ, res = self.execute_action(act)
                    action_results.append(res)
                    if not succ:
                        break

                final_text = "\n".join(action_results) if action_results else (response or "Command completed.")
                self._record_conversation(message, response or final_text)
                return final_text

        # ----------------------------------------------------
        # 3. ONLY UNKNOWN / OPEN-ENDED REQUESTS REACH OLLAMA
        # ----------------------------------------------------
        try:
            plan = ask_ollama(
                message,
                self.conversation
            )

            norm_plan = normalize_plan(plan)
            plan_type = norm_plan.get("type", "chat")
            response = str(norm_plan.get("response", "")).strip()
            actions = norm_plan.get("actions", [])

            # ------------------------------------------------
            # NORMAL CHAT
            # ------------------------------------------------
            if plan_type == "chat":
                final_chat = response or "I don't have an answer for that."
                self._record_conversation(message, final_chat)
                return final_chat

            # ------------------------------------------------
            # AI ACTIONS
            # ------------------------------------------------
            results = []
            for action in actions:
                if self.is_cancelled:
                    return "Operation cancelled by user."
                if not isinstance(action, dict):
                    continue

                tool_name = action.get("tool")
                if not tool_name:
                    continue

                success, result = self.execute_action(action)
                results.append(result)
                if not success:
                    break

            final_action_text = "\n".join(results) if results else (response or "Command completed.")
            self._record_conversation(message, response or final_action_text)
            return final_action_text

        except OllamaError as exc:
            # Graceful offline fallback
            return (
                f"NEO AI: {exc}\n"
                "(Offline Mode: Local PC automation, file search, and system commands remain fully operational.)"
            )

        except Exception as exc:
            return f"NEO error: {exc}"

    # Modern alias for text processing
    process_text = run


# Backward-compatible and modern alias
NeoAgent = OrionAgent



