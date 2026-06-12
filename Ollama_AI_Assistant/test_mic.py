import speech_recognition as sr

recognizer = sr.Recognizer()
# IMPORTANT: Adjust the duration (1-3 seconds). The room must be relatively quiet.
# It listens for 2 seconds to understand your background noise level.
DURATION = 2

try:
    with sr.Microphone() as source:
        print(f"🔇 Calibrating microphone for {DURATION} seconds... (Please keep quiet)")
        # This is the line that fixes the "timed out" error.
        # It measures the background noise and lowers the threshold.
        recognizer.adjust_for_ambient_noise(source, duration=DURATION)
        
        # This line shows you the new sensitivity level.
        # A lower number (e.g., 50-200) means it's more sensitive.
        print(f"✅ Calibration complete. Energy threshold set to: {recognizer.energy_threshold}")
        print("🎤 Say something!")
        
        # Now listen for what you say.
        audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
        print("🎧 Processing...")

        # Recognize using Google's service.
        text = recognizer.recognize_google(audio)
        print(f"✅ You said: {text}")

except sr.WaitTimeoutError:
    print("❌ Timeout: No speech detected. Please speak louder or check your mic.")
except sr.UnknownValueError:
    print("❌ Google Speech Recognition could not understand the audio.")
except sr.RequestError as e:
    print(f"❌ Could not request results from Google Speech Recognition service; {e}")
except Exception as e:
    print(f"❌ An unexpected error occurred: {e}")