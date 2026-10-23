import pyttsx3

try:
    engine = pyttsx3.init()
    voices = engine.getProperty("voices")
    print(f"Total SAPI5 voices found: {len(voices)}")
    for idx, v in enumerate(voices):
        print(f"[{idx}] ID: {v.id}")
        print(f"    Name: {v.name}")
        print(f"    Languages: {getattr(v, 'languages', [])}")
        print(f"    Gender: {getattr(v, 'gender', 'Unknown')}")
except Exception as e:
    print(f"Error checking SAPI5: {e}")
