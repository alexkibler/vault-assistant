#!/usr/bin/env python3
"""Test audio transcription with monitoring."""

import requests
import json
import sys
from pathlib import Path

audio_file = Path("/Users/alex/Library/Mobile Documents/com~apple~CloudDocs/Yellow Creek Rd.m4a")

if not audio_file.exists():
    print(f"Error: Audio file not found: {audio_file}")
    sys.exit(1)

print(f"Audio file: {audio_file.name}")
print(f"Size: {audio_file.stat().st_size / 1024 / 1024:.2f} MB")
print("")

url = "http://localhost:8765/transcribe-and-capture"
print(f"Sending to: {url}")
print("This may take a while for Whisper to load and process...\n")

try:
    with open(audio_file, "rb") as f:
        files = {"audio": f}
        response = requests.post(url, files=files, timeout=600)

    print(f"Status: {response.status_code}")
    print("\nResponse:")
    print(json.dumps(response.json(), indent=2))

except requests.exceptions.Timeout:
    print("ERROR: Request timed out (600s)")
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
