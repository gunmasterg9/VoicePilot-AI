import asyncio
import edge_tts
import io
import sys
import soundfile as sf

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

async def test_synthesis():
    test_cases = [
        ("en-US-AriaNeural", "Hello! NEO AI is operational and ready to assist you on your PC."),
        ("en-US-GuyNeural", "Good day. NEO audio synthesis is functioning properly."),
        ("hi-IN-SwaraNeural", "नमस्ते! नियो एआई आपकी सेवा के लिए तैयार है।"),
        ("hi-IN-MadhurNeural", "नमस्कार। मैं नियो हूँ, आपका लोकल एआई पीसी सहायक।"),
        ("gu-IN-DhwaniNeural", "નમસ્તે! નિયો એઆઈ તમારા પીસી પર તમારી મદદ માટે તૈયાર છે."),
        ("gu-IN-NiranjanNeural", "કેમ છો? હું નિયો છું, તમારો લોકલ આસિસ્ટન્ટ.")
    ]

    print("\n--- Testing Edge TTS Speech Synthesis for All 6 Voices ---")
    for voice, text in test_cases:
        print(f"Synthesizing [{voice}] -> \"{text[:30]}...\"")
        try:
            communicate = edge_tts.Communicate(text, voice)
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            
            if not audio_data:
                print(f"  [FAIL] {voice}: Returned 0 bytes of audio data.")
                continue

            # Verify audio is valid MP3 readable by soundfile
            data, samplerate = sf.read(io.BytesIO(audio_data))
            duration = len(data) / samplerate
            print(f"  [PASS] {voice}: Generated {len(audio_data)} bytes ({duration:.2f}s audio @ {samplerate}Hz)")
        except Exception as exc:
            print(f"  [FAIL] {voice}: Exception {exc}")

if __name__ == "__main__":
    asyncio.run(test_synthesis())
