import os
import requests
import re
from typing import Optional, Dict

from config.settings import OUTPUT_DIR

TTS_API_URL = "http://127.0.0.1:8000/api/tts"
DEFAULT_VOICE = "af_alloy"

# --- NEW: Define the speeds we want to pre-generate ---
TARGET_SPEEDS = [1.0, 1.5, 2.0]

# Pre-compiled regex to filter un-speakable text
BAD_TEXT_PATTERN = re.compile(r"^([\W\s_]|[a-zA-Z](?=\s|$))+$")

class TTSGenerator:
    def __init__(self) -> None:
        self.output_dir: str = OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)
        # Health check remains the same
        try:
            requests.get("http://127.0.0.1:8000/health", timeout=3).raise_for_status()
            print("✅ TTS service is healthy and connected.")
        except requests.exceptions.RequestException as e:
            print(f"❌ CRITICAL: Could not connect to the TTS service at {TTS_API_URL}. Please ensure it's running. Error: {e}")

    # The generate function now returns a DICTIONARY of URLs, not a single string
    def generate(self, text: str, bubble_order: int, unique_prefix: str) -> Optional[Dict[str, str]]:
        cleaned_text = text.strip()
        if not cleaned_text or BAD_TEXT_PATTERN.match(cleaned_text):
            if cleaned_text:
                print(f"  -> Skipping TTS for un-speakable text in bubble {bubble_order}: '{cleaned_text}'")
            return None

        audio_urls = {}

        # Loop through each target speed and generate an audio file for it
        for speed in TARGET_SPEEDS:
            # Create a unique filename for each speed
            speed_str = str(speed).replace('.', '_') # e.g., '1_0', '1_5'
            audio_filename = f"{unique_prefix}_bubble_{bubble_order}_speed_{speed_str}.wav"
            audio_path = os.path.join(self.output_dir, audio_filename)
            
            payload = {
                "input": cleaned_text,
                "voice": DEFAULT_VOICE,
                "response_format": "wav",
                "speed": speed # Pass the current speed to the API
            }
            
            try:
                print(f"Requesting TTS for bubble {bubble_order} at {speed}x speed...")
                response = requests.post(TTS_API_URL, json=payload, timeout=45)
                response.raise_for_status()

                with open(audio_path, 'wb') as f:
                    f.write(response.content)
                
                if os.path.exists(audio_path):
                    # Add the successful URL to our dictionary
                    # The key is a string version of the speed for JSON compatibility
                    audio_urls[str(speed)] = f"/static/results/{audio_filename}"
                else:
                    print(f"  -> Error: Audio file was not created for speed {speed}x.")

            except requests.exceptions.RequestException as e:
                print(f"❌ TTS API request failed for bubble {bubble_order} at {speed}x: {e}")
                # Continue to the next speed even if one fails
                continue
        
        # Return the dictionary of all generated URLs, or None if all failed
        return audio_urls if audio_urls else None