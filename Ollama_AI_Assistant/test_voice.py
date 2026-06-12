import pyttsx3
import time

engine = pyttsx3.init()

# List all available voices
voices = engine.getProperty('voices')
print("Available voices:")
for i, voice in enumerate(voices):
    print(f"{i}: {voice.name}")

# Try to speak
print("\nTrying to speak...")
engine.say("Hello, this is a test of the female voice")
engine.runAndWait()
print("Done!")

# Try female voice if available
for voice in voices:
    if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
        engine.setProperty('voice', voice.id)
        print(f"\nNow using female voice: {voice.name}")
        engine.say("This is the female voice speaking")
        engine.runAndWait()
        break