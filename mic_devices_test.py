import speech_recognition as sr

devices = [2, 8, 14, 17]

for index in devices:
    names = sr.Microphone.list_microphone_names()
    print("\n" + "=" * 45)
    print(f"Testing device {index}: {names[index]}")
    r = sr.Recognizer()
    r.dynamic_energy_threshold = True
    r.pause_threshold = 0.8

    try:
        with sr.Microphone(device_index=index) as source:
            print("Stay quiet for calibration...")
            r.adjust_for_ambient_noise(source, duration=0.7)
            print("Threshold:", round(r.energy_threshold, 1))
            print("SPEAK NOW: What time is it?")

            try:
                audio = r.listen(
                    source, timeout=5, phrase_time_limit=4
                )
                print("SUCCESS: Audio captured,", len(audio.frame_data), "bytes")
            except sr.WaitTimeoutError:
                print("FAIL: No speech detected on this device.")

    except Exception as e:
        print("DEVICE ERROR:", type(e).__name__, str(e))
