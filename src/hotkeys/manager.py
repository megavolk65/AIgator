"""
Менеджер горячих клавиш

Использует Windows RegisterHotKey API для перехвата горячих клавиш.
Работает на уровне ОС — не блокируется играми и не вызывает
срабатывания античитов (в отличие от keyboard hooks).
"""

import sys
import os
import json
import ctypes
import ctypes.wintypes
import threading
from PyQt6.QtCore import QObject, pyqtSignal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import config

# Windows API константы
WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

# Hotkey IDs
HOTKEY_OVERLAY_ID = 1
HOTKEY_SCREENSHOT_ID = 2

# Маппинг названий клавиш -> Virtual Key Codes
VK_MAP = {
    'insert': 0x2D, 'ins': 0x2D,
    'delete': 0x2E, 'del': 0x2E,
    'home': 0x24,
    'end': 0x23,
    'pageup': 0x21, 'page_up': 0x21, 'pgup': 0x21,
    'pagedown': 0x22, 'page_down': 0x22, 'pgdown': 0x22, 'pgdn': 0x22,
    'pause': 0x13,
    'scroll_lock': 0x91, 'scrolllock': 0x91,
    'print_screen': 0x2C, 'printscreen': 0x2C,
    'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73,
    'f5': 0x74, 'f6': 0x75, 'f7': 0x76, 'f8': 0x77,
    'f9': 0x78, 'f10': 0x79, 'f11': 0x7A, 'f12': 0x7B,
    'space': 0x20,
    'enter': 0x0D, 'return': 0x0D,
    'tab': 0x09,
    'backspace': 0x08,
    'escape': 0x1B, 'esc': 0x1B,
    'numpad0': 0x60, 'numpad1': 0x61, 'numpad2': 0x62,
    'numpad3': 0x63, 'numpad4': 0x64, 'numpad5': 0x65,
    'numpad6': 0x66, 'numpad7': 0x67, 'numpad8': 0x68,
    'numpad9': 0x69,
}

# Маппинг модификаторов
MOD_MAP = {
    'ctrl': MOD_CONTROL, 'control': MOD_CONTROL,
    'alt': MOD_ALT,
    'shift': MOD_SHIFT,
    'win': MOD_WIN, 'windows': MOD_WIN,
}

user32 = ctypes.windll.user32


class HotkeyManager(QObject):
    """Менеджер глобальных горячих клавиш через Windows RegisterHotKey API"""
    
    # Сигналы
    toggle_overlay = pyqtSignal()
    take_screenshot = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self._enabled = True
        self._thread = None
        self._thread_id = None
        self._running = False
        
        # Загружаем горячие клавиши из настроек
        self.hotkey_overlay_str, self.hotkey_screenshot_str = self._load_hotkeys_from_settings()
    
    def _load_hotkeys_from_settings(self):
        """Загрузить горячие клавиши из settings.json"""
        try:
            if getattr(sys, 'frozen', False):
                base_path = os.path.dirname(sys.executable)
            else:
                base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
            settings_path = os.path.join(base_path, "settings.json")
            with open(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                return (
                    settings.get('hotkey_overlay', 'Insert'),
                    settings.get('hotkey_screenshot', 'Home')
                )
        except:
            return ('Insert', 'Home')
    
    def _parse_hotkey(self, hotkey_str: str):
        """Преобразовать строку горячей клавиши в (modifiers, vk_code)"""
        parts = hotkey_str.lower().replace(' ', '').split('+')
        
        modifiers = MOD_NOREPEAT  # Без автоповтора
        vk_code = 0
        
        for part in parts:
            if part in MOD_MAP:
                modifiers |= MOD_MAP[part]
            elif part in VK_MAP:
                vk_code = VK_MAP[part]
            elif len(part) == 1 and part.isalpha():
                vk_code = ord(part.upper())
            elif len(part) == 1 and part.isdigit():
                vk_code = ord(part)
            else:
                print(f"[HotkeyManager] Неизвестная клавиша: {part}")
        
        return modifiers, vk_code
    
    def _message_loop(self):
        """Цикл сообщений Windows в отдельном потоке"""
        self._thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
        
        # Регистрируем горячие клавиши в этом потоке
        overlay_mod, overlay_vk = self._parse_hotkey(self.hotkey_overlay_str)
        screenshot_mod, screenshot_vk = self._parse_hotkey(self.hotkey_screenshot_str)
        
        if overlay_vk:
            if not user32.RegisterHotKey(None, HOTKEY_OVERLAY_ID, overlay_mod, overlay_vk):
                print(f"[HotkeyManager] Не удалось зарегистрировать: {self.hotkey_overlay_str}")
        
        if screenshot_vk:
            if not user32.RegisterHotKey(None, HOTKEY_SCREENSHOT_ID, screenshot_mod, screenshot_vk):
                print(f"[HotkeyManager] Не удалось зарегистрировать: {self.hotkey_screenshot_str}")
        
        # Цикл сообщений
        msg = ctypes.wintypes.MSG()
        while self._running:
            ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if ret <= 0:
                break
            
            if msg.message == WM_HOTKEY:
                if not self._enabled:
                    continue
                
                if msg.wParam == HOTKEY_OVERLAY_ID:
                    self.toggle_overlay.emit()
                elif msg.wParam == HOTKEY_SCREENSHOT_ID:
                    self.take_screenshot.emit()
        
        # Снимаем регистрацию при выходе
        user32.UnregisterHotKey(None, HOTKEY_OVERLAY_ID)
        user32.UnregisterHotKey(None, HOTKEY_SCREENSHOT_ID)
    
    def register_hotkeys(self):
        """Зарегистрировать все горячие клавиши"""
        try:
            self.unregister_hotkeys()
            
            self._running = True
            self._thread = threading.Thread(target=self._message_loop, daemon=True)
            self._thread.start()
            
            return True
        except Exception as e:
            print(f"[HotkeyManager] Ошибка регистрации: {e}")
            return False
    
    def unregister_hotkeys(self):
        """Отменить регистрацию всех горячих клавиш"""
        if self._running and self._thread_id:
            self._running = False
            # WM_QUIT чтобы GetMessage вернул 0
            user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)
            if self._thread:
                self._thread.join(timeout=2)
            self._thread = None
            self._thread_id = None
    
    def update_hotkeys(self, hotkey_overlay: str = None, hotkey_screenshot: str = None):
        """Обновить горячие клавиши"""
        if hotkey_overlay:
            self.hotkey_overlay_str = hotkey_overlay
        if hotkey_screenshot:
            self.hotkey_screenshot_str = hotkey_screenshot
        self.register_hotkeys()
    
    def set_enabled(self, enabled: bool):
        """Включить/выключить обработку горячих клавиш"""
        self._enabled = enabled
    
    @property
    def is_enabled(self) -> bool:
        """Включены ли горячие клавиши"""
        return self._enabled
    
    def get_hotkey_description(self) -> dict:
        """Получить описание горячих клавиш"""
        return {
            "toggle_overlay": self.hotkey_overlay_str,
            "screenshot": self.hotkey_screenshot_str,
        }
