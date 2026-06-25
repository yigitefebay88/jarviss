"""
System control helper for Windows automation.
"""

from __future__ import annotations

import subprocess
import ctypes
from pathlib import Path


def _get_foreground_window() -> int | None:
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        return hwnd if hwnd else None
    except Exception:
        return None


def control_window(action: str) -> str:
    hwnd = _get_foreground_window()
    if not hwnd:
        return "Aktif pencere bulunamadı."

    try:
        action = (action or "").lower()
        if action == "close":
            ctypes.windll.user32.PostMessageW(hwnd, 0x0010, 0, 0)
            return "Aktif pencere kapatılıyor."
        if action == "minimize":
            ctypes.windll.user32.ShowWindow(hwnd, 6)
            return "Aktif pencere simge durumuna küçültüldü."
        if action == "maximize":
            ctypes.windll.user32.ShowWindow(hwnd, 3)
            return "Aktif pencere büyütüldü."
        if action == "restore":
            ctypes.windll.user32.ShowWindow(hwnd, 9)
            return "Aktif pencere geri getirildi."
        return "Geçersiz window_control işlemi. close, minimize, maximize veya restore kullan."
    except Exception as exc:
        return f"Pencere kontrolü yapılamadı: {exc}"


def _send_sendkeys(sequence: str) -> tuple[bool, str]:
    if sequence is None:
        return False, "Gönderilecek tuş dizisi boş olamaz."
    safe = str(sequence).replace("'", "''")
    script = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        f"[System.Windows.Forms.SendKeys]::SendWait('{safe}')"
    )
    try:
        subprocess.run(
            ["powershell", "-WindowStyle", "Hidden", "-Command", script],
            check=False,
            timeout=20,
        )
        return True, "Tuş dizisi gönderildi."
    except Exception as exc:
        return False, f"Tuş dizisi gönderilemedi: {exc}"


def send_keys(keys: str) -> str:
    ok, message = _send_sendkeys(keys)
    return message


def type_text(text: str) -> str:
    if text is None:
        return "Yazılacak metin boş olamaz."
    return send_keys(text)


def run_system_command(command: str) -> str:
    if not command or not str(command).strip():
        return "Çalıştırılacak komut belirtilmedi."
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
        if result.returncode == 0:
            output = (result.stdout or "").strip()
            return output or "Komut başarıyla çalıştırıldı."
        stderr = (result.stderr or "").strip()
        return f"Komut çalıştı ancak hata kodu döndü: {result.returncode}. {stderr}"
    except Exception as exc:
        return f"Komut çalıştırılamadı: {exc}"
