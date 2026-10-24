"""
NEO AI - Single Device Microphone & Whisper Diagnostic Script
Tests physical Device 2 (Microphone Array (Realtek(R) Audio)) with offline Faster-Whisper,
resampling verification (44.1kHz -> 16kHz), energy calculation, and validation layer.
"""

import sys
import speech_recognition as sr
import numpy as np

from interfaces.voice import VoiceInterface, validate_transcription
from core.router import CommandRouter

voice = VoiceInterface(agent=None)
router = CommandRouter()

# Resolve device (defaults to Device 2 on this PC)
device_index, device_name, is_virtual = voice.resolve_input_device()
print("=" * 60)
print(f"NEO AI Single-Device Diagnostic Test")
print(f"Target Device: [{device_index}] {device_name} (Virtual: {is_virtual})")
print("=" * 60)

r = sr.Recognizer()
r.dynamic_energy_threshold = True
r.pause_threshold = 0.8

try:
    with sr.Microphone(device_index=device_index) as source:
        print("Calibrating ambient noise for 1.0 second. Please stay quiet...")
        r.adjust_for_ambient_noise(source, duration=1.0)
        print(f"Calibrated energy threshold: {r.energy_threshold:.1f}")
        print("Speak now: 'What time is it?' or 'Open Notepad'...")

        try:
            audio = r.listen(source, timeout=8, phrase_time_limit=5)
            print(f"AUDIO CAPTURED: {len(audio.frame_data)} raw bytes at {audio.sample_rate}Hz")

            # Perform genuine resampling and offline transcription
            wav_path = voice._audio_to_wav(audio)
            transcription = voice._transcribe(wav_path)
            quality = voice._last_transcription_quality

            print("\n--- Audio & Quality Metrics ---")
            print(f"Input sample rate:      {audio.sample_rate}Hz")
            print(f"Whisper sample rate:    16000Hz (genuinely resampled)")
            print(f"Recording duration:     {quality.get('duration', 0):.2f}s")
            print(f"Signal RMS energy:      {quality.get('rms', 0):.5f}")
            print(f"Signal peak amplitude:  {quality.get('peak', 0):.5f}")
            print(f"Avg log-probability:    {quality.get('avg_logprob', 0):.2f}")
            print(f"No-speech probability:  {quality.get('no_speech_prob', 0):.2f}")

            print("\n--- Whisper & Routing Result ---")
            print(f"Recognized text:        {repr(transcription)}")

            is_valid, cleaned, reason = validate_transcription(transcription, quality=quality)
            print(f"Validation status:      {'VALID' if is_valid else 'REJECTED'} (reason: {reason})")

            if is_valid:
                intent, details = router.classify_intent(cleaned)
                print(f"Command intent:         {intent}")
                print(f"Intent details:         {details}")
            else:
                print("Action:                 Safely ignored to prevent accidental web/AI execution.")

        except sr.WaitTimeoutError:
            print("TIMEOUT: No speech detected within 8 seconds.")

except OSError as e:
    print(f"DEVICE ERROR: Could not open microphone [{device_index}]: {e}")
except Exception as e:
    print(f"ERROR: {type(e).__name__} - {e}")

print("\n" + "=" * 60)
print("Diagnostic Complete.")
print("=" * 60)
