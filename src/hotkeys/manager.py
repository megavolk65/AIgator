"""
Менеджер горячих клавиш

Использует библиотеку keyboard для глобального перехвата клавиш,
в том числе в полноэкранных играх.
"""

import sys
import os
import json
from typing import Optional
import keyboard
from PyQt6.QtCore import QObject, pyqtSignal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import config


class HotkeyManager(QObject):
    """Менеджер глобальных горячих клавиш"""
    
    # Сигналы
    toggle_overlay = pyqtSignal()
    take_screenshot = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self._enabled = True
        self._hotkey_ids = []  # ID зарегистрированных hotkey
        
        # Загружаем горячие клавиши из настроек
        hotkey_overlay_str, hotkey_screenshot_str = self._load_hotkeys_from_settings()
        
        # Сохраняем строковые значения
        self.hotkey_overlay = self._normalize_hotkey(hotkey_overlay_str)
        self.hotkey_screenshot = self._normalize_hotkey(hotkey_screenshot_str)
    
    def _load_hotkeys_from_settings(self):
        """Загрузить горячие клавиши из settings.json"""
        try:
            settings_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "settings.json"
            )
            with open(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                return (
                    settings.get('hotkey_overlay', 'Insert'),
                    settings.get('hotkey_screenshot', 'Home')
                )
        except:
            return ('Insert', 'Home')
    
    def _normalize_hotkey(self, hotkey_str: str) -> str:
        """Нормализовать строку горячей клавиши для библиотеки keyboard"""
        # Маппинг названий клавиш
        key_map = {
            'ins': 'insert',
            'del': 'delete',
            'pageup': 'page up',
            'page_up': 'page up',
            'pgup': 'page up',
            'pagedown': 'page down',
            'page_down': 'page down',
            'pgdn': 'page down',
            'scroll_lock': 'scroll lock',
            'print_screen': 'print screen',
            'printscreen': 'print screen',
            'prtsc': 'print screen',
        }
        
        key_lower = hotkey_str.lower().strip()
        return key_map.get(key_lower, key_lower)
    
    def register_hotkeys(self):
        """Зарегистрировать все горячие клавиши"""
        try:
            # Сначала отменяем старые
            self.unregister_hotkeys()
            
            # Регистрируем горячую клавишу для оверлея
            keyboard.add_hotkey(
                self.hotkey_overlay,
                self._on_toggle_overlay,
                suppress=True  # Подавляем передачу клавиши другим приложениям
            )
            self._hotkey_ids.append(self.hotkey_overlay)
            
            # Регистрируем горячую клавишу для скриншота
            keyboard.add_hotkey(
                self.hotkey_screenshot,
                self._on_take_screenshot,
                suppress=True
            )
            self._hotkey_ids.append(self.hotkey_screenshot)
            
            return True
            
        except Exception as e:
            print(f"Ошибка регистрации горячих клавиш: {e}")
            return False
    
    def unregister_hotkeys(self):
        """Отменить регистрацию всех горячих клавиш"""
        for hotkey in self._hotkey_ids:
            try:
                keyboard.remove_hotkey(hotkey)
            except:
                pass
        self._hotkey_ids.clear()
    
    def _on_toggle_overlay(self):
        """Обработчик горячей клавиши оверлея"""
        if self._enabled:
            self.toggle_overlay.emit()
    
    def _on_take_screenshot(self):
        """Обработчик горячей клавиши скриншота"""
        if self._enabled:
            self.take_screenshot.emit()
    
    def update_hotkeys(self, hotkey_overlay: str = None, hotkey_screenshot: str = None):
        """Обновить горячие клавиши без перезапуска"""
        if hotkey_overlay:
            self.hotkey_overlay = self._normalize_hotkey(hotkey_overlay)
        if hotkey_screenshot:
            self.hotkey_screenshot = self._normalize_hotkey(hotkey_screenshot)
        
        # Перерегистрируем
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
            "toggle_overlay": self.hotkey_overlay,
            "screenshot": self.hotkey_screenshot,
        }
