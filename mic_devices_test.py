"""
NEO AI - Multi-Device Hardware Diagnostic Script
Tests physical microphones [2, 8, 14, 17] with safe stream uninitialization guards,
computes audio metrics (RMS, peak, clipping, duration), and verifies local Faster-Whisper.
"""

import sys
from pathlib import Path
import speech_recognition as sr
import numpy as np

# Apply safe context manager patch from interfaces.voice
from interfaces.voice import VoiceInterface, validate_transcription

devices = [2, 8, 14, 17]
names = sr.Microphone.list_microphone_names()

print("=" * 60)
print("NEO AI Hardware Microphone Diagnostic Test")
print("=" * 60)

voice = VoiceInterface(agent=None)

for index in devices:
    if index >= len(names):
        continue

    print("\n" + "-" * 50)
    print(f"Testing Device [{index}]: {names[index]}")
    r = sr.Recognizer()
    r.dynamic_energy_threshold = True
    r.pause_threshold = 0.8

    try:
        with sr.Microphone(device_index=index) as source:
            print("Calibrating ambient noise (0.7s)...")
            r.adjust_for_ambient_noise(source, duration=0.7)
            print(f"Calibrated energy threshold: {r.energy_threshold:.1f}")
            print("SPEAK NOW: 'What time is it' or 'Open Notepad'...")

            try:
                audio = r.listen(source, timeout=5, phrase_time_limit=4)
                print(f"SUCCESS: Audio captured ({len(audio.frame_data)} raw bytes, sample_rate={audio.sample_rate}Hz)")

                # Test genuine resampling to 16kHz mono float32
                wav_path = voice._audio_to_wav(audio)
                transcript = voice._transcribe(wav_path)
                quality = voice._last_transcription_quality

                print(f"RESAMPLED METRICS: sample_rate=16000Hz, duration={quality.get('duration', 0):.2f}s, "
                      f"RMS={quality.get('rms', 0):.4f}, peak={quality.get('peak', 0):.4f}")
                print(f"LOCAL WHISPER RESULT: {repr(transcript)}")

                is_valid, cleaned, reason = validate_transcription(transcript, quality=quality)
                print(f"VALIDATION RESULT: is_valid={is_valid}, cleaned='{cleaned}', reason='{reason}'")

            except sr.WaitTimeoutError:
                print("FAIL: No speech detected within 5 seconds.")

    except OSError as e:
        print(f"DEVICE ERROR (Expected for non-capture endpoint): OSError - {e}")
    except Exception as e:
        print(f"UNEXPECTED ERROR: {type(e).__name__} - {e}")

print("\n" + "=" * 60)
print("Hardware Diagnostic Test Finished.")
print("=" * 60)
