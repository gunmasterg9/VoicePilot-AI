import speech_recognition as sr

r = sr.Recognizer()
r.dynamic_energy_threshold = True
r.pause_threshold = 0.8

print("Opening microphone...")

try:
    with sr.Microphone() as source:
        print("Calibrating for 1 second. Please stay quiet...")
        r.adjust_for_ambient_noise(source, duration=1)
        print("Energy threshold:", r.energy_threshold)
        print("Speak now: What time is it?")

        audio = r.listen(source, timeout=8, phrase_time_limit=5)
        print("AUDIO CAPTURED:", len(audio.frame_data), "bytes")

        print("Testing Whisper-independent Google recognition...")
        try:
            print("Recognized:", r.recognize_google(audio))
        except sr.UnknownValueError:
            print("Audio captured, but speech was not understood.")
        except sr.RequestError as e:
            print("Recognition service/network error:", e)

except sr.WaitTimeoutError:
    print("TIMEOUT: No speech detected within 8 seconds.")
except Exception as e:
    print(type(e).__name__ + ":", e)
