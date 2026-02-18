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

# Добавляем путь к модулям
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QObject, QTimer, pyqtSlot

import config
from src.overlay import OverlayWindow
from src.hotkeys import HotkeyManager
from src.game_detect import ContextDetector
from src.screenshot import ScreenCapture
from src.ai.yandex_gpt_rest import YandexGPTRestClient
from src.ai import YandexVisionClient


class AIHelperApp(QObject):
    """Главное приложение"""
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        super().__init__(self.app)
        self.app.setQuitOnLastWindowClosed(False)  # Не закрывать при скрытии окна
        
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
        self.gpt_client = YandexGPTRestClient()
        self.vision_client = YandexVisionClient()
        
        # Захват экрана
        self.screen_capture = ScreenCapture()
        
        # Оверлей
        self.overlay = OverlayWindow(
            gpt_client=self.gpt_client,
            context_detector=self.context_detector
        )
        
        # Менеджер горячих клавиш
        self.hotkey_manager = HotkeyManager()
    
    def _init_tray(self):
        """Инициализация системного трея"""
        # Иконка
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.ico")
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
        else:
            # Используем стандартную иконку если своей нет
            icon = self.app.style().standardIcon(
                self.app.style().StandardPixmap.SP_ComputerIcon
            )
        
        # Создаём трей
        self.tray = QSystemTrayIcon(icon, self.app)
        self.tray.setToolTip(f"{config.APP_NAME} v{config.APP_VERSION}")
        
        # Контекстное меню
        menu = QMenu()
        
        # Показать/скрыть
        show_action = QAction("Показать", self.app)
        show_action.triggered.connect(self._toggle_overlay)
        menu.addAction(show_action)
        
        menu.addSeparator()
        
        # Горячие клавиши
        hotkeys_menu = menu.addMenu("Горячие клавиши")
        hotkeys_menu.addAction(f"Оверлей: {config.HOTKEY_TOGGLE_OVERLAY}")
        hotkeys_menu.addAction(f"Скриншот: {config.HOTKEY_SCREENSHOT}")
        
        # Автозагрузка
        self.autostart_action = QAction("Автозапуск", self.app)
        self.autostart_action.setCheckable(True)
        self.autostart_action.setChecked(self._is_autostart_enabled())
        self.autostart_action.triggered.connect(self._toggle_autostart)
        menu.addAction(self.autostart_action)
        
        menu.addSeparator()
        
        # Очистить чат
        clear_action = QAction("Очистить чат", self.app)
        clear_action.triggered.connect(self._clear_chat)
        menu.addAction(clear_action)
        
        menu.addSeparator()
        
        # Выход
        quit_action = QAction("Выход", self.app)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)
        
        self.tray.setContextMenu(menu)
        
        # Клик по иконке
        self.tray.activated.connect(self._on_tray_activated)
        
        # Показываем трей
        self.tray.show()
    
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
        # Делаем скриншот
        screenshot_base64 = self.screen_capture.capture_and_encode(monitor=1)
        
        if screenshot_base64:
            # Анализируем через Vision API
            context = self.vision_client.analyze_screenshot(screenshot_base64)
            
            # Передаём контекст в оверлей
            self.overlay.set_screenshot_context(context)
            
            # Показываем уведомление
            self.tray.showMessage(
                config.APP_NAME,
                "📷 Скриншот сделан и прикреплён к сообщению",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
        else:
            self.tray.showMessage(
                config.APP_NAME,
                "❌ Ошибка создания скриншота",
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
    
    def _toggle_autostart(self):
        """Переключить автозагрузку"""
        try:
            key = self._get_autostart_key()
            
            if self.autostart_action.isChecked():
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
                self.tray.showMessage(
                    config.APP_NAME,
                    "Автозапуск включён",
                    QSystemTrayIcon.MessageIcon.Information,
                    2000
                )
            else:
                # Выключить автозапуск
                try:
                    winreg.DeleteValue(key, config.APP_NAME)
                except WindowsError:
                    pass
                self.tray.showMessage(
                    config.APP_NAME,
                    "Автозапуск выключен",
                    QSystemTrayIcon.MessageIcon.Information,
                    2000
                )
            
            winreg.CloseKey(key)
            
        except Exception as e:
            self.tray.showMessage(
                config.APP_NAME,
                f"Ошибка настройки автозапуска: {e}",
                QSystemTrayIcon.MessageIcon.Warning,
                3000
            )
    
    def run(self):
        """Запуск приложения"""
        # Показываем уведомление о запуске
        self.tray.showMessage(
            config.APP_NAME,
            f"Запущен! Нажмите {config.HOTKEY_TOGGLE_OVERLAY} для вызова",
            QSystemTrayIcon.MessageIcon.Information,
            3000
        )
        
        return self.app.exec()


def main():
    """Главная функция"""
    # Проверяем, что приложение не запущено
    # (можно добавить проверку через файл блокировки или named mutex)
    
    app = AIHelperApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
