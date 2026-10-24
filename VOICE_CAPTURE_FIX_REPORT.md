# NEO AI Voice Capture Fix Report

## Findings
- The microphone test measures raw input energy with PyAudio; it does not verify that SpeechRecognition's voice activity threshold triggers.
- `VoiceInterface.listen_once()` previously made one listen attempt after ambient-noise calibration. If the calibrated threshold was too high for quiet speech, the command ended with a timeout even when the device meter showed activity.
- The uploaded `launch_neo.bat` also used `python main.py --mode ui`, but `main.py` does not define `--mode`. The desktop GUI is the default mode.

## Changes
- `interfaces/voice.py`: log the calibrated threshold, retry once after a speech-trigger timeout using a bounded temporary threshold, and restore the original threshold/dynamic-threshold setting afterward. The temporary sensitivity change is not persisted.
- `tests/test_microphone_subsystem.py`: add a regression test for first-timeout / second-attempt-success and update timeout expectations.
- `launch_neo.bat`: launch the GUI using `python main.py`.
- The archive omits generated `__pycache__`, `.pyc`, runtime cache, and `data/settings.json` so the user's local settings are not overwritten.

## Verification performed here
- Python source compilation: PASS (`compileall`).
- ZIP creation and archive integrity: checked.
- Automated microphone tests: NOT RUN in this environment because `speech_recognition` is not installed. The added regression test must be run on the Windows environment with project dependencies installed.
- Physical microphone capture and Whisper transcription: NOT VERIFIED here.

## Windows verification
1. Extract this archive to a new folder or back up the existing project first.
2. Install the repository's requirements in the intended Python environment.
3. Run `python -m unittest tests.test_microphone_subsystem -v`.
4. Run `python main.py` (or `launch_neo.bat`), press VOICE, wait for the calibrated-threshold log, and speak a short phrase after `Speak now...`.
5. If it still times out, share the log lines showing selected microphone, calibrated threshold, sensitivity retry threshold, and final timeout. Do not share API keys or `.env`.
