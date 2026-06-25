from __future__ import annotations

import os
import threading

from android_ui import AndroidJarvisUI
from main import JarvisLive


def main():
    if os.environ.get("TERM_PROGRAM") == "vscode":
        print("[JARVIS] Android başlatıcısı VS Code içinden çalışıyor.")

    ui = AndroidJarvisUI()

    def runner():
        ui.wait_for_api_key()
        jarvis = JarvisLive(ui)
        try:
            import asyncio
            asyncio.run(jarvis.run())
        except KeyboardInterrupt:
            print("\n🔴 Kapatılıyor...")

    threading.Thread(target=runner, daemon=True).start()
    ui.run()


if __name__ == "__main__":
    main()
