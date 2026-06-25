from __future__ import annotations

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

from app_config import has_gemini_api_key


class AndroidJarvisRoot(BoxLayout):
    def __init__(self, ui: "AndroidJarvisUI", **kwargs):
        super().__init__(**kwargs)
        self.ui = ui
        self.orientation = "vertical"
        self.spacing = 4
        self.padding = 8

        self.state_label = Label(
            text="Başlatılıyor...",
            size_hint=(1, None),
            height=36,
            halign="left",
            valign="middle",
        )
        self.state_label.bind(size=self._refresh_label)
        self.add_widget(self.state_label)

        self.log_output = TextInput(
            text="",
            readonly=True,
            background_color=(0.02, 0.05, 0.05, 1),
            foreground_color=(0.88, 0.97, 0.97, 1),
            font_size=14,
            size_hint=(1, 1),
            halign="left",
            valign="top",
        )
        self.log_output.bind(texture_size=self._update_scroll)

        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(self.log_output)
        self.add_widget(scroll)

        self.command_input = TextInput(
            text="",
            size_hint=(1, None),
            height=44,
            multiline=False,
            hint_text="Komut yazıp Enter'a basın...",
            font_size=16,
        )
        self.command_input.bind(on_text_validate=self._on_send)

        send_button = Button(
            text="Gönder",
            size_hint=(None, None),
            size=(110, 44),
            on_press=self._on_send,
        )

        bottom_bar = BoxLayout(size_hint=(1, None), height=48, spacing=4)
        bottom_bar.add_widget(self.command_input)
        bottom_bar.add_widget(send_button)
        self.add_widget(bottom_bar)

    def _refresh_label(self, *_):
        self.state_label.text_size = (self.state_label.width, None)

    def _update_scroll(self, *_):
        pass

    def _on_send(self, instance):
        text = self.command_input.text.strip()
        if text and self.ui.on_text_command:
            self.ui.on_text_command(text)
        self.command_input.text = ""


class AndroidJarvisApp(App):
    def __init__(self, ui: "AndroidJarvisUI", **kwargs):
        super().__init__(**kwargs)
        self.ui = ui

    def build(self) -> Widget:
        Window.clearcolor = (0.01, 0.04, 0.04, 1)
        return self.ui.root


class AndroidJarvisUI:
    def __init__(self):
        self.on_text_command = None
        self.on_pause_toggle = None
        self.on_effects_state_change = None
        self.muted = False
        self.root = AndroidJarvisRoot(self)
        self._state = "INITIALISING"
        self._log_lines: list[str] = []
        self._update_state_label()

    def _schedule(self, callback, *args):
        Clock.schedule_once(lambda dt: callback(*args), 0)

    def _update_state_label(self):
        self._schedule(lambda: setattr(self.root.state_label, "text", f"Durum: {self._state}"))

    def set_state(self, state: str):
        self._state = state
        self._update_state_label()

    def write_log(self, text: str):
        if not text:
            return
        self._log_lines.append(text)
        if len(self._log_lines) > 200:
            self._log_lines = self._log_lines[-200:]
        self._schedule(self._refresh_log)

    def _refresh_log(self):
        self.root.log_output.text = "\n".join(self._log_lines)
        self.root.log_output.cursor = (0, len(self.root.log_output.text.splitlines()))

    def write_debug(self, text: str, level: str = "INFO"):
        self.write_log(f"[{level}] {text}")

    def focus_panel(self, panel_name: str, duration_ms: int = 1000):
        self.write_log(f"Panel odaklanıyor: {panel_name}")

    def mark_user_activity(self, active: bool):
        pass

    def play_success_sfx(self):
        pass

    def wait_for_api_key(self):
        if not has_gemini_api_key():
            self.write_log("Gemini API anahtarı eksik. config/api_keys.json içine ekleyin.")
            while not has_gemini_api_key():
                pass

    def wake_up(self):
        self.write_log("Wake gesture tetiklendi.")

    def run(self):
        AndroidJarvisApp(self).run()
