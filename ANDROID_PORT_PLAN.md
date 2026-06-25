# Android Port Plan for JARVIS

This project is currently a Windows/Tkinter app. Porting it to Android requires a rewrite of the UI layer and removal of Windows-specific system calls.

## What must change

1. Replace `ui.py` and Tkinter usage with an Android-compatible UI.
   - Recommended frameworks: Kivy, BeeWare/Toga, or an Android-specific Python runtime.
   - `JarvisUI` should be reimplemented for Android.

2. Remove or replace Windows-only modules:
   - `ctypes` / `user32` usage in `actions/system_control.py`
   - PowerShell-based commands in `actions/open_app.py`, `actions/system_control.py`, and `ui.py`
   - `pyautogui` or desktop automation that assumes Windows environment

3. Replace camera handling:
   - Android cameras must be accessed through Android APIs or an IP webcam stream.
   - The current `ui.py` uses OpenCV and `cv2.VideoCapture`; this is not guaranteed on Android.

4. Replace audio playback and microphone capture:
   - Current audio depends on `sounddevice`/PyAudio and PowerShell sound playback.
   - Android should use a native audio layer or Kivy/Android audio APIs.

5. Preserve core business logic:
   - `main.py`, `actions/*.py`, and Gemini integration can remain mostly unchanged if UI and platform wrappers are abstracted.
   - Keep the tool handlers and AI logic separate from the UI.

## First porting steps

- Create an Android-specific UI module (e.g. `android_ui.py`).
- Create an Android entrypoint (e.g. `android_main.py`) that instantiates `JarvisLive` with the Android UI.
- Use config values to control `camera_source` and other device-specific settings.

## Practical recommendation

The easiest path is not to run this Windows app directly on Android, but to:

- Use the PC version of JARVIS as the core logic engine,
- Access the phone camera as an IP webcam stream,
- Or, build a separate Android frontend that connects to the existing backend.
