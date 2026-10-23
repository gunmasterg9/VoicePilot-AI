import urllib.request
import json

url = "https://raw.githubusercontent.com/rhasspy/piper/master/VOICES.md"
try:
    req = urllib.request.Request(
        "https://huggingface.co/rhasspy/piper-voices/raw/main/voices.json",
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=8) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        print(f"Total Piper voice keys: {len(data)}")
        
        hi_voices = [k for k in data.keys() if k.startswith("hi_") or "hindi" in k.lower()]
        gu_voices = [k for k in data.keys() if k.startswith("gu_") or "gujarati" in k.lower()]
        en_voices = [k for k in data.keys() if k.startswith("en_")]
        
        print(f"Piper Hindi voices: {hi_voices}")
        print(f"Piper Gujarati voices: {gu_voices}")
        print(f"Piper English sample voices: {en_voices[:5]}")
except Exception as e:
    print(f"Error querying piper voices: {e}")
