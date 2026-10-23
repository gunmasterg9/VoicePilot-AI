import asyncio
import edge_tts

async def check():
    print("Fetching voice list from Edge TTS service...")
    try:
        voices = await edge_tts.list_voices()
    except Exception as e:
        print(f"Failed to fetch voices: {e}")
        return

    targets = [
        "en-US-AriaNeural",
        "en-US-GuyNeural",
        "hi-IN-SwaraNeural",
        "hi-IN-MadhurNeural",
        "gu-IN-DhwaniNeural",
        "gu-IN-NiranjanNeural"
    ]
    
    found = {v["ShortName"]: v for v in voices}
    for t in targets:
        if t in found:
            info = found[t]
            print(f"[FOUND] {t} | Locale: {info.get('Locale')} | Gender: {info.get('Gender')}")
        else:
            print(f"[MISSING] {t}")
            
    # Also find all Gujarati and Hindi voices in Edge TTS
    print("\n--- All available Gujarati voices ---")
    gu_voices = [v["ShortName"] for v in voices if "gu" in v.get("Locale", "").lower()]
    print(gu_voices)
    
    print("\n--- All available Hindi voices ---")
    hi_voices = [v["ShortName"] for v in voices if "hi" in v.get("Locale", "").lower()]
    print(hi_voices)

if __name__ == "__main__":
    asyncio.run(check())
