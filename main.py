"""
AI Helper - Главная точка входа

Универсальный AI-ассистент с оверлеем на базе YandexGPT.
Горячие клавиши:
- Ctrl+Shift+G: открыть/скрыть оверлей
- Ctrl+Shift+S: сделать скриншот
- Escape: закрыть оверлей
"""

import sys
import os
import winreg
import ctypes
import shutil

# Добавляем путь к модулям
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _ensure_settings():
    """Создать settings.json из default если не существует"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    settings_path = os.path.join(base_dir, "settings.json")
    default_path = os.path.join(base_dir, "settings.default.json")
    
    if not os.path.exists(settings_path) and os.path.exists(default_path):
        shutil.copy(default_path, settings_path)


# Создаём settings.json при первом запуске
_ensure_settings()

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QObject, QTimer, pyqtSlot

import config
from src.localization import t, Localization
from src.overlay import OverlayWindow
from src.hotkeys import HotkeyManager
from src.game_detect import ContextDetector
from src.screenshot import ScreenCapture
from src.ai.openrouter_client import OpenRouterClient


class AIHelperApp(QObject):
    """Главное приложение"""
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        super().__init__(self.app)
        self.app.setQuitOnLastWindowClosed(False)  # Не закрывать при скрытии окна
        
        # Загружаем язык ДО создания компонентов
        self._load_language()
        
        # Инициализация компонентов
        self._init_components()
        self._init_tray()
        self._init_hotkeys()
        self._connect_signals()
        
        # Запуск
        if not config.START_MINIMIZED:
            self.overlay.show()
    
    def _init_components(self):
        """Инициализация компонентов"""
        # Детектор контекста
        self.context_detector = ContextDetector()
        
        # AI клиенты
        self.gpt_client = OpenRouterClient()  # Используем OpenRouter с Gemma 3 27B
        
        # Захват экрана
        self.screen_capture = ScreenCapture()
        
        # Оверлей
        self.overlay = OverlayWindow(
            gpt_client=self.gpt_client,
            context_detector=self.context_detector
        )
        self.overlay.autostart_checker = self._is_autostart_enabled
        
        # Менеджер горячих клавиш
        self.hotkey_manager = HotkeyManager()
    
    def _init_tray(self):
        """Инициализация системного трея"""
        # Иконка
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.ico")
        if os.path.exists(icon_path):
            self._tray_icon = QIcon(icon_path)
        else:
            # Используем стандартную иконку если своей нет
            self._tray_icon = self.app.style().standardIcon(
                self.app.style().StandardPixmap.SP_ComputerIcon
            )
        
        # Создаём трей
        self.tray = QSystemTrayIcon(self._tray_icon, self.app)
        
        # Клик по иконке
        self.tray.activated.connect(self._on_tray_activated)
        
        # Создаём меню
        self._create_tray_menu()
        
        # Подписываемся на смену языка
        Localization.add_listener(self._create_tray_menu)
        
        # Показываем трей
        self.tray.show()
    
    def _load_language(self):
        """Загрузить язык из настроек"""
        import json
        settings_path = os.path.join(os.path.dirname(__file__), "settings.json")
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                lang = settings.get("language", "ru")
                Localization.set_language(lang)
        except:
            pass
    
    def _create_tray_menu(self):
        """Создать/пересоздать меню трея"""
        # Обновляем tooltip
        self.tray.setToolTip(f"{t('app_name')} v{config.APP_VERSION}")
        
        # Создаём новое меню
        menu = QMenu()
        
        # Показать/скрыть
        show_action = QAction(t("show"), self.app)
        show_action.triggered.connect(self._toggle_overlay)
        menu.addAction(show_action)
        
        menu.addSeparator()
        
        # Очистить чат
        clear_action = QAction(t("clear_chat"), self.app)
        clear_action.triggered.connect(self._clear_chat)
        menu.addAction(clear_action)
        
        menu.addSeparator()
        
        # Выход
        quit_action = QAction(t("exit"), self.app)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)
        
        self.tray.setContextMenu(menu)
    
    def _init_hotkeys(self):
        """Инициализация горячих клавиш"""
        self.hotkey_manager.register_hotkeys()
    
    def _connect_signals(self):
        """Подключение сигналов"""
        # Горячие клавиши
        self.hotkey_manager.toggle_overlay.connect(self._toggle_overlay)
        self.hotkey_manager.take_screenshot.connect(self._take_screenshot)
        
        # Оверлей
        self.overlay.screenshot_requested.connect(self._take_screenshot)
        self.overlay.hotkeys_changed.connect(self._on_hotkeys_changed)
        self.overlay.autostart_changed.connect(self._set_autostart)
    
    def _on_hotkeys_changed(self, hotkey_overlay: str, hotkey_screenshot: str):
        """Обработчик изменения горячих клавиш"""
        self.hotkey_manager.update_hotkeys(hotkey_overlay, hotkey_screenshot)
        self.tray.showMessage(
            config.APP_NAME,
            t("settings_applied"),
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )
    
    def _toggle_overlay(self):
        """Переключить видимость оверлея"""
        self.overlay.toggle_visibility()
    
    def _take_screenshot(self):
        """Сделать скриншот"""
        # Скрываем оверлей на время скриншота
        was_visible = self.overlay.isVisible()
        if was_visible:
            self.overlay.hide()
        
        # Небольшая задержка чтобы окно успело скрыться
        QTimer.singleShot(100, lambda: self._capture_and_process(was_visible))
    
    def _capture_and_process(self, show_after: bool):
        """Захват и обработка скриншота"""
        # Делаем скриншот активного окна
        screenshot_pil = self.screen_capture.capture_active_window()
        
        if screenshot_pil:
            # Конвертируем в base64 для Vision API
            import base64
            from io import BytesIO
            
            buffer = BytesIO()
            screenshot_pil.save(buffer, format='PNG')
            screenshot_bytes = buffer.getvalue()
            screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
            
            # Передаём изображение напрямую в оверлей (Gemini сам его проанализирует)
            context = "Скриншот активного окна"
            self.overlay.set_screenshot_context(context, screenshot_bytes)
            
            # Показываем уведомление
            self.tray.showMessage(
                config.APP_NAME,
                t("screenshot_taken"),
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
        else:
            self.tray.showMessage(
                config.APP_NAME,
                t("screenshot_error"),
                QSystemTrayIcon.MessageIcon.Warning,
                2000
            )
        
        # Показываем оверлей обратно
        if show_after:
            self.overlay.show()
            self.overlay.activateWindow()
            self.overlay.input_field.setFocus()
    
    @pyqtSlot(QSystemTrayIcon.ActivationReason)
    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason):
        """Обработка клика по иконке трея"""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._toggle_overlay()
    
    
    def _clear_chat(self):
        """Очистить чат"""
        self.overlay._clear_chat()
    
    def _quit(self):
        """Выход из приложения"""
        self.hotkey_manager.unregister_hotkeys()
        self.tray.hide()
        self.app.quit()
    
    # === Автозагрузка ===
    
    def _get_autostart_key(self):
        """Получить ключ реестра для автозапуска"""
        return winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_ALL_ACCESS
        )
    
    def _is_autostart_enabled(self) -> bool:
        """Проверить, включена ли автозагрузка"""
        try:
            key = self._get_autostart_key()
            winreg.QueryValueEx(key, config.APP_NAME)
            winreg.CloseKey(key)
            return True
        except WindowsError:
            return False
    
    def _set_autostart(self, enabled: bool):
        """Установить автозагрузку"""
        try:
            key = self._get_autostart_key()
            
            if enabled:
                # Включить автозапуск
                exe_path = sys.executable
                if exe_path.endswith("python.exe") or exe_path.endswith("pythonw.exe"):
                    # Запуск через Python
                    script_path = os.path.abspath(__file__)
                    value = f'"{exe_path}" "{script_path}"'
                else:
                    # Скомпилированный exe
                    value = f'"{exe_path}"'
                
                winreg.SetValueEx(key, config.APP_NAME, 0, winreg.REG_SZ, value)
            else:
                # Выключить автозапуск
                try:
                    winreg.DeleteValue(key, config.APP_NAME)
                except WindowsError:
                    pass
            
            winreg.CloseKey(key)
            
        except Exception as e:
            self.tray.showMessage(
                config.APP_NAME,
                f"{t('autostart_error')} {e}",
                QSystemTrayIcon.MessageIcon.Warning,
                3000
            )
    
    def run(self):
        """Запуск приложения"""
        # Получаем актуальную горячую клавишу из настроек
        hotkey = self.hotkey_manager.hotkey_overlay or config.HOTKEY_TOGGLE_OVERLAY
        
        # Показываем уведомление о запуске
        self.tray.showMessage(
            config.APP_NAME,
            t("started_press_key").format(key=hotkey),
            QSystemTrayIcon.MessageIcon.Information,
            3000
        )
        
        return self.app.exec()


def is_already_running():
    """Проверка через Windows Mutex"""
    MUTEX_NAME = "AIHelper_SingleInstance_Mutex"
    
    # Пытаемся создать mutex
    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    
    # Если mutex уже существует - приложение уже запущено
    ERROR_ALREADY_EXISTS = 183
    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        return True
    
    return False


def main():
    """Главная функция"""
    # Проверяем, что приложение не запущено
    if is_already_running():
        # Можно показать сообщение или просто выйти
        sys.exit(0)
    
    app = AIHelperApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
