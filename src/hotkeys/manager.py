"""
Менеджер горячих клавиш

Использует pynput для низкоуровневого перехвата клавиш,
лучше работает в полноэкранных играх.
"""

import sys
import os
import json
import threading
from typing import Optional, Callable
from pynput import keyboard
from pynput.keyboard import Key, KeyCode
from PyQt6.QtCore import QObject, pyqtSignal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import config


# Маппинг строковых названий в pynput Key
KEY_MAP = {
    'insert': Key.insert,
    'ins': Key.insert,
    'delete': Key.delete,
    'del': Key.delete,
    'home': Key.home,
    'end': Key.end,
    'page_up': Key.page_up,
    'pageup': Key.page_up,
    'pgup': Key.page_up,
    'page_down': Key.page_down,
    'pagedown': Key.page_down,
    'pgdn': Key.page_down,
    'pause': Key.pause,
    'scroll_lock': Key.scroll_lock,
    'print_screen': Key.print_screen,
    'f1': Key.f1, 'f2': Key.f2, 'f3': Key.f3, 'f4': Key.f4,
    'f5': Key.f5, 'f6': Key.f6, 'f7': Key.f7, 'f8': Key.f8,
    'f9': Key.f9, 'f10': Key.f10, 'f11': Key.f11, 'f12': Key.f12,
    'space': Key.space,
    'enter': Key.enter,
    'tab': Key.tab,
    'backspace': Key.backspace,
    'escape': Key.esc,
    'esc': Key.esc,
    'ctrl': Key.ctrl,
    'alt': Key.alt,
    'shift': Key.shift,
}


class HotkeyManager(QObject):
    """Менеджер глобальных горячих клавиш"""
    
    # Сигналы
    toggle_overlay = pyqtSignal()
    take_screenshot = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self._enabled = True
        self._listener = None
        self._pressed_keys = set()
        
        # Загружаем горячие клавиши из настроек
        hotkey_overlay_str, hotkey_screenshot_str = self._load_hotkeys_from_settings()
        
        # Сохраняем строковые значения
        self.hotkey_overlay_str = hotkey_overlay_str
        self.hotkey_screenshot_str = hotkey_screenshot_str
        
        # Преобразуем в pynput ключи
        self.hotkey_overlay = self._parse_hotkey(hotkey_overlay_str)
        self.hotkey_screenshot = self._parse_hotkey(hotkey_screenshot_str)
    
    def _load_hotkeys_from_settings(self):
        """Загрузить горячие клавиши из settings.json"""
        try:
            # Определяем базовый путь
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
        """Преобразовать строку горячей клавиши в набор pynput ключей"""
        keys = set()
        parts = hotkey_str.lower().replace(' ', '').split('+')
        
        for part in parts:
            if part in KEY_MAP:
                keys.add(KEY_MAP[part])
            elif len(part) == 1:
                # Одиночный символ
                keys.add(KeyCode.from_char(part))
            else:
                # Попробуем как специальную клавишу
                try:
                    keys.add(getattr(Key, part))
                except AttributeError:
                    print(f"Неизвестная клавиша: {part}")
        
        return frozenset(keys)
    
    def _on_press(self, key):
        """Обработчик нажатия клавиши"""
        if not self._enabled:
            return
        
        # Нормализуем клавишу
        normalized_key = self._normalize_key(key)
        self._pressed_keys.add(normalized_key)
        
        # Проверяем совпадения
        if self._check_hotkey(self.hotkey_overlay):
            self.toggle_overlay.emit()
        elif self._check_hotkey(self.hotkey_screenshot):
            self.take_screenshot.emit()
    
    def _on_release(self, key):
        """Обработчик отпускания клавиши"""
        normalized_key = self._normalize_key(key)
        self._pressed_keys.discard(normalized_key)
    
    def _normalize_key(self, key):
        """Нормализовать клавишу (объединить left/right модификаторы)"""
        # Объединяем левые/правые модификаторы
        if key in (Key.ctrl_l, Key.ctrl_r):
            return Key.ctrl
        elif key in (Key.alt_l, Key.alt_r, Key.alt_gr):
            return Key.alt
        elif key in (Key.shift_l, Key.shift_r):
            return Key.shift
        return key
    
    def _check_hotkey(self, hotkey: frozenset) -> bool:
        """Проверить, нажата ли комбинация"""
        if not hotkey:
            return False
        return hotkey <= self._pressed_keys
    
    def register_hotkeys(self):
        """Зарегистрировать все горячие клавиши"""
        try:
            # Сначала отменяем старые
            self.unregister_hotkeys()
            
            # Запускаем слушателя в отдельном потоке
            self._listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release,
                suppress=False  # Не блокируем клавиши
            )
            self._listener.start()
            
            return True
            
        except Exception as e:
            print(f"Ошибка регистрации горячих клавиш: {e}")
            return False
    
    def unregister_hotkeys(self):
        """Отменить регистрацию всех горячих клавиш"""
        if self._listener:
            try:
                self._listener.stop()
            except:
                pass
            self._listener = None
        self._pressed_keys.clear()
    
    def update_hotkeys(self, hotkey_overlay: str = None, hotkey_screenshot: str = None):
        """Обновить горячие клавиши без перезапуска"""
        if hotkey_overlay:
            self.hotkey_overlay_str = hotkey_overlay
            self.hotkey_overlay = self._parse_hotkey(hotkey_overlay)
        if hotkey_screenshot:
            self.hotkey_screenshot_str = hotkey_screenshot
            self.hotkey_screenshot = self._parse_hotkey(hotkey_screenshot)
    
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
