"""
NEO AI - Settings & Persistence Manager
Handles loading, updating, and saving user configuration with backward-compatible migration.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict

from config import DATA_DIR, OLLAMA_MODEL, MICROPHONE_INDEX, NEO_NAME

SETTINGS_FILE = DATA_DIR / "settings.json"

DEFAULT_SETTINGS: Dict[str, Any] = {
    # Application & Identity
    "app_name": "NEO AI",
    "assistant_name": NEO_NAME,
    "tagline": "Your Local AI PC Assistant",

    # AI Brain (100% Local & Offline)
    "ai_provider": "ollama",
    "ollama_host": "http://127.0.0.1:11434",
    "ollama_model": OLLAMA_MODEL,
    "llm_timeout": 60,
    "max_history_turns": 8,

    # Speech Recognition
    "whisper_model": "tiny.en",
    "speech_language": "en",          # "en", "hi", "gu", or "auto"
    "mic_device_index": MICROPHONE_INDEX, # None = Auto-detect best physical mic
    "mic_device_name": "",            # Persisted device name for index shift resilience
    "mic_energy_threshold": 300,      # Base energy threshold (150-2500)
    "mic_dynamic_energy": True,       # Adaptive threshold tracking
    "mic_ambient_duration": 0.4,      # Noise calibration duration (seconds)

    # Text to Speech
    "tts_enabled": True,              # Master toggle for voice output
    "tts_provider": "offline",        # "offline" (sapi5) default for 100% offline operation
    "tts_voice_online": "en-US-AriaNeural",
    "tts_voice_offline_index": 0,
    "tts_output_device_index": None,  # None = System default output
    "tts_speech_rate": 180,
    "tts_volume": 1.0,

    # Automation & Safety
    "confirm_destructive_actions": True,
    "allow_external_websites": True,

    # UI Preferences
    "auto_scroll_transcript": True,
    "show_telemetry": True
}


class SettingsManager:
    """Manages persistent application configuration with migration."""

    def __init__(self, filepath: Path = SETTINGS_FILE):
        self.filepath = filepath
        self._settings: Dict[str, Any] = {}
        self.load()

    def load(self) -> Dict[str, Any]:
        """Loads settings from disk, applying defaults and migrations."""
        self._settings = dict(DEFAULT_SETTINGS)

        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                if isinstance(saved, dict):
                    # Backward-compatible migration of legacy keys (ignoring obsolete cloud keys)
                    obsolete_cloud_keys = {"cloud_api_key", "cloud_base_url", "cloud_model"}
                    migrated = {}
                    for k, v in saved.items():
                        if k in obsolete_cloud_keys:
                            continue
                        lower_k = k.lower()
                        if lower_k.startswith("orion_"):
                            suffix = lower_k[6:]
                            if suffix in ["ai_model", "model"]:
                                migrated["ollama_model"] = v
                                migrated["ai_model"] = v
                            elif suffix in ["tts_mode", "tts_provider"]:
                                migrated["tts_provider"] = v
                                migrated["tts_mode"] = v
                            elif suffix in ["name", "assistant_name"]:
                                migrated["assistant_name"] = v
                            elif suffix not in obsolete_cloud_keys:
                                migrated[suffix] = v
                        else:
                            migrated[k] = v
                    self._settings.update(migrated)
            except Exception as exc:
                print(f"[WARN] Failed to read settings file: {exc}. Using defaults.")

        return self._settings

    def save(self) -> bool:
        """Persists current settings to disk (guaranteeing no cloud keys are written)."""
        try:
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            # Ensure obsolete cloud keys are never written to disk
            clean_settings = {
                k: v for k, v in self._settings.items()
                if k not in {"cloud_api_key", "cloud_base_url", "cloud_model"}
            }
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(clean_settings, f, indent=4, ensure_ascii=False)
            return True
        except Exception as exc:
            print(f"[ERROR] Failed to save settings: {exc}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        if key in {"cloud_api_key", "cloud_base_url", "cloud_model"}:
            return "" if key == "cloud_api_key" else default
        return self._settings.get(key, default if default is not None else DEFAULT_SETTINGS.get(key))

    def set(self, key: str, value: Any, save: bool = True) -> None:
        self._settings[key] = value
        if save:
            self.save()

    def update(self, mapping: Dict[str, Any], save: bool = True) -> None:
        self._settings.update(mapping)
        if save:
            self.save()

    def all(self) -> Dict[str, Any]:
        return dict(self._settings)


# Global singleton instance
settings = SettingsManager()
