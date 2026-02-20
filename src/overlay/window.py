"""
Главное окно оверлея
"""

import re
import sys
import os
import ctypes
from typing import Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextBrowser, QLineEdit, QPushButton, QLabel,
    QApplication, QSizeGrip, QComboBox, QStyledItemDelegate, QStyle, QStyleOptionComboBox, QStylePainter
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl, QByteArray, QTimer
import json
from PyQt6.QtGui import QFont, QTextCursor, QDesktopServices, QPixmap, QColor, QIcon

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from .styles import DARK_THEME, CHAT_MESSAGE_CSS
from .settings_dialog import SettingsDialog
from .web_dialog import WebDialog
import config

from src.localization import Localization, t
from src.updater import check_for_updates, get_current_version, get_releases_url
from version import GITHUB_REPO


class ModelItemDelegate(QStyledItemDelegate):
    """Делегат для отображения моделей с приглушённым названием компании"""
    
    def paint(self, painter, option, index):
        text = index.data(Qt.ItemDataRole.DisplayRole)
        if not text:
            super().paint(painter, option, index)
            return
        
        # Фон при выделении/наведении
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        elif option.state & QStyle.StateFlag.State_MouseOver:
            painter.fillRect(option.rect, QColor("#3a3a5a"))
        
        # Парсим: "COMPANY: MODEL — PRICE"
        if ": " in text:
            company, model = text.split(": ", 1)
            company += ": "
        else:
            company, model = "", text
        
        painter.save()
        text_rect = option.rect.adjusted(5, 0, -5, 0)
        
        # Компания — приглушённо
        if company:
            painter.setPen(QColor("#888888"))
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, company)
            company_width = painter.fontMetrics().horizontalAdvance(company)
            text_rect = text_rect.adjusted(company_width, 0, 0, 0)
        
        # Модель — ярко
        painter.setPen(QColor("#ffffff"))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, model)
        
        painter.restore()


class StyledModelComboBox(QComboBox):
    """Кастомный ComboBox с приглушённым названием компании"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setItemDelegate(ModelItemDelegate(self))
    
    def paintEvent(self, event):
        painter = QStylePainter(self)
        
        # Рисуем рамку ComboBox
        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)
        painter.drawComplexControl(QStyle.ComplexControl.CC_ComboBox, opt)
        
        # Получаем текущий текст
        text = self.currentText()
        if not text:
            return
        
        # Парсим: "COMPANY: MODEL — PRICE"
        if ": " in text:
            company, model = text.split(": ", 1)
            company += ": "
        else:
            company, model = "", text
        
        # Область для текста
        text_rect = self.style().subControlRect(
            QStyle.ComplexControl.CC_ComboBox, opt,
            QStyle.SubControl.SC_ComboBoxEditField, self
        )
        text_rect = text_rect.adjusted(2, 0, 0, 0)
        
        # Компания — приглушённо
        if company:
            painter.setPen(QColor("#888888"))
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, company)
            company_width = painter.fontMetrics().horizontalAdvance(company)
            text_rect = text_rect.adjusted(company_width, 0, 0, 0)
        
        # Модель — ярко
        painter.setPen(QColor("#ffffff"))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, model)


class UpdateCheckerWorker(QThread):
    """Фоновый поток для проверки обновлений"""
    update_available = pyqtSignal(str, str)  # (new_version, release_url)
    no_update = pyqtSignal()
    
    def run(self):
        try:
            result = check_for_updates()
            if result:
                self.update_available.emit(result[0], result[1])
            else:
                self.no_update.emit()
        except:
            self.no_update.emit()


class BalanceWorker(QThread):
    """Фоновый поток для получения баланса"""
    balance_ready = pyqtSignal(dict)  # {balance, currency, provider}
    
    def __init__(self, gpt_client):
        super().__init__()
        self.gpt_client = gpt_client
    
    def run(self):
        try:
            result = self.gpt_client.get_balance()
            provider = self.gpt_client.get_provider_name()
            if result:
                result["provider"] = provider
                self.balance_ready.emit(result)
            else:
                self.balance_ready.emit({"provider": provider, "balance": None, "currency": ""})
        except:
            pass


class AIWorker(QThread):
    """Фоновый поток для запросов к AI"""
    response_ready = pyqtSignal(str)
    response_chunk = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, gpt_client, message: str, screenshot_context: str = "", image_data: bytes = None):
        super().__init__()
        self.gpt_client = gpt_client
        self.message = message
        self.screenshot_context = screenshot_context
        self.image_data = image_data
    
    def run(self):
        try:
            # Если есть изображение - используем send_request
            if self.image_data:
                response = self.gpt_client.send_request(
                    self.message,
                    image_data=self.image_data
                )
            else:
                # Иначе обычный текстовый запрос
                response = self.gpt_client.send_message(
                    self.message,
                    screenshot_context=self.screenshot_context
                )
            self.response_ready.emit(response)
        except Exception as e:
            self.error_occurred.emit(str(e))


class OverlayWindow(QMainWindow):
    """Главное окно оверлея"""
    
    # Сигналы
    screenshot_requested = pyqtSignal()
    hide_requested = pyqtSignal()
    hotkeys_changed = pyqtSignal(str, str)  # hotkey_overlay, hotkey_screenshot
    autostart_changed = pyqtSignal(bool)  # Изменение автозапуска
    
    def __init__(self, gpt_client=None, context_detector=None):
        super().__init__()
        
        self.gpt_client = gpt_client
        self.context_detector = context_detector
        self._current_screenshot_context = ""
        self._current_screenshot_image: Optional[QPixmap] = None
        self._current_screenshot_bytes: Optional[bytes] = None  # Байты изображения
        self._current_app_context = ""  # Название активного окна/игры
        self._worker: Optional[AIWorker] = None
        self._balance_worker: Optional[BalanceWorker] = None
        self._update_worker: Optional[UpdateCheckerWorker] = None
        self._new_version: Optional[str] = None  # Новая версия если есть
        self._new_version_url: Optional[str] = None
        self._chat_history_html = ""
        self._showing_setup_instruction = False  # Флаг: показана ли инструкция
        self.autostart_checker = None  # Функция для проверки состояния автозапуска
        
        # Загружаем язык из настроек
        self._load_language()
        
        self._setup_window()
        self._setup_ui()
        self._apply_styles()
        self._update_context()  # Устанавливаем контекст один раз при старте
        self._update_balance()  # Загружаем баланс при старте
        self._check_for_updates()  # Проверяем обновления при старте
        
        # Подписываемся на смену языка
        Localization.add_listener(self._update_ui_texts)
    
    def _setup_window(self):
        """Настройка окна"""
        self.setWindowTitle(t("app_name"))
        
        # Иконка окна (для панели задач)
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # Флаги окна для работы поверх полноэкранных игр
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        
        # Атрибуты для оверлея
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, False)  # Активируем окно
        
        # Прозрачность
        self.setWindowOpacity(config.OVERLAY_OPACITY)
        
        # Применяем Windows-специфичные флаги после показа окна
        self._apply_windows_overlay_flags()
        
        # Размеры
        self.resize(config.OVERLAY_WIDTH, config.OVERLAY_HEIGHT)
        
        # Позиционирование
        self._position_window()
    
    def _apply_windows_overlay_flags(self):
        """Применить Windows-специфичные флаги для работы поверх игр"""
        try:
            import ctypes
            from ctypes import wintypes
            
            # Константы Windows API
            GWL_EXSTYLE = -20
            WS_EX_TOPMOST = 0x00000008
            WS_EX_LAYERED = 0x00080000
            WS_EX_TRANSPARENT = 0x00000020
            HWND_TOPMOST = -1
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_NOACTIVATE = 0x0010
            
            # Получаем HWND окна
            hwnd = int(self.winId())
            
            # Получаем текущие флаги
            user32 = ctypes.windll.user32
            ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            
            # Добавляем флаги для оверлея
            ex_style |= WS_EX_LAYERED | WS_EX_TOPMOST
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
            
            # Устанавливаем окно поверх всех
            user32.SetWindowPos(
                hwnd, HWND_TOPMOST,
                0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
            )
            
        except Exception as e:
            print(f"Warning: Failed to apply Windows overlay flags: {e}")
    
    def _force_focus_from_game(self):
        """Принудительно забрать фокус у игры через AttachThreadInput"""
        try:
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            
            # Получаем HWND нашего окна
            our_hwnd = int(self.winId())
            
            # Получаем HWND окна на переднем плане (игра)
            foreground_hwnd = user32.GetForegroundWindow()
            
            if foreground_hwnd == 0 or foreground_hwnd == our_hwnd:
                # Если мы уже в фокусе или нет окна на переднем плане
                return
            
            # Получаем ID потоков
            foreground_thread = user32.GetWindowThreadProcessId(foreground_hwnd, None)
            our_thread = kernel32.GetCurrentThreadId()
            
            if foreground_thread == 0 or our_thread == 0:
                return
            
            # Подключаемся к потоку ввода игры
            user32.AttachThreadInput(foreground_thread, our_thread, True)
            
            try:
                # Забираем фокус
                user32.SetForegroundWindow(our_hwnd)
                user32.SetFocus(our_hwnd)
                self.activateWindow()
                self.raise_()
            finally:
                # Отключаемся от потока ввода
                user32.AttachThreadInput(foreground_thread, our_thread, False)
            
        except Exception as e:
            print(f"Warning: Failed to force focus: {e}")
            # Fallback на стандартные методы
            self.activateWindow()
            self.raise_()
    
    def _position_window(self):
        """Позиционирование окна на экране"""
        screen = QApplication.primaryScreen()
        if not screen:
            return
        
        screen_geometry = screen.availableGeometry()
        
        if config.OVERLAY_POSITION == "center":
            x = (screen_geometry.width() - self.width()) // 2
            y = (screen_geometry.height() - self.height()) // 2
        elif config.OVERLAY_POSITION == "top-right":
            x = screen_geometry.width() - self.width() - 20
            y = 20
        elif config.OVERLAY_POSITION == "bottom-right":
            x = screen_geometry.width() - self.width() - 20
            y = screen_geometry.height() - self.height() - 20
        else:
            x = (screen_geometry.width() - self.width()) // 2
            y = (screen_geometry.height() - self.height()) // 2
        
        self.move(x, y)
    
    def _setup_ui(self):
        """Создание UI"""
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Основной layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        
        # === Заголовок ===
        header_layout = QHBoxLayout()
        
        # Кнопка переключения языка
        self.lang_btn = QPushButton()
        self.lang_btn.setObjectName("langButton")
        self.lang_btn.setFixedSize(50, 24)
        self.lang_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lang_btn.clicked.connect(self._toggle_language)
        self._update_lang_button()
        header_layout.addWidget(self.lang_btn)
        
        # Название
        self.title_label = QLabel("")
        self.title_label.setObjectName("titleLabel")
        header_layout.addWidget(self.title_label)
        self.title_label.setText(t("app_name"))
        
        # Версия (мелким серым шрифтом, кликабельная)
        self.version_label = QLabel("")
        self.version_label.setStyleSheet("color: #6c757d; font-size: 11px;")
        self.version_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.version_label.setToolTip(f"GitHub: {GITHUB_REPO}")
        self.version_label.mousePressEvent = self._on_version_click
        header_layout.addWidget(self.version_label)
        self.version_label.setText(f"v{get_current_version()}")
        
        header_layout.addStretch()
        
        # Кнопка обновления контекста
        self.refresh_context_btn = QPushButton("↻")
        self.refresh_context_btn.setObjectName("refreshContextButton")
        self.refresh_context_btn.setFixedSize(28, 28)
        self.refresh_context_btn.setToolTip(t("refresh_context"))
        self.refresh_context_btn.clicked.connect(self._update_context)
        header_layout.addWidget(self.refresh_context_btn)
        
        # Контекст (игра/приложение)
        self.context_label = QLabel(t("not_detected"))
        self.context_label.setObjectName("contextLabel")
        header_layout.addWidget(self.context_label)
        
        # Кнопка закрытия
        self.close_btn = QPushButton("X")
        self.close_btn.setObjectName("closeButton")
        self.close_btn.setFixedSize(30, 30)
        self.close_btn.clicked.connect(self.hide)
        header_layout.addWidget(self.close_btn)
        
        main_layout.addLayout(header_layout)
        
        # === Область чата с кнопкой очистки поверх ===
        chat_container = QWidget()
        chat_container_layout = QVBoxLayout(chat_container)
        chat_container_layout.setContentsMargins(0, 0, 0, 0)
        chat_container_layout.setSpacing(0)
        
        # Создаём внутренний контейнер для наложения
        chat_inner = QWidget()
        chat_container_layout.addWidget(chat_inner, 1)
        
        self.chat_display = QTextBrowser(chat_inner)
        self.chat_display.setOpenExternalLinks(False)
        self.chat_display.setOpenLinks(False)  # Предотвращаем сброс содержимого при клике
        self.chat_display.anchorClicked.connect(self._handle_link_click)
        self.chat_display.setPlaceholderText(t("ask_question"))
        
        # Кнопка очистки поверх чата (правый нижний угол)
        self.clear_btn = QPushButton(t("clear_chat"), chat_inner)
        self.clear_btn.setObjectName("clearButton")
        self.clear_btn.clicked.connect(self._clear_chat)
        self.clear_btn.raise_()  # Поверх чата
        
        # Сохраняем ссылку на внутренний контейнер для resizeEvent
        self._chat_inner = chat_inner
        
        main_layout.addWidget(chat_container, 1)
        
        # === Превью скриншота ===
        self.screenshot_preview_container = QWidget()
        screenshot_preview_layout = QVBoxLayout(self.screenshot_preview_container)
        screenshot_preview_layout.setContentsMargins(0, 5, 0, 5)
        screenshot_preview_layout.setSpacing(5)
        
        preview_header = QHBoxLayout()
        self.preview_label = QLabel(t("screenshot_preview"))
        self.preview_label.setStyleSheet("color: #4fc3f7; font-size: 12px; font-weight: bold;")
        preview_header.addWidget(self.preview_label)
        
        remove_preview_btn = QPushButton("X")
        remove_preview_btn.setFixedSize(20, 20)
        remove_preview_btn.setObjectName("removePreviewButton")
        remove_preview_btn.clicked.connect(self._remove_screenshot)
        preview_header.addWidget(remove_preview_btn)
        preview_header.addStretch()
        
        screenshot_preview_layout.addLayout(preview_header)
        
        self.screenshot_preview = QLabel()
        self.screenshot_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.screenshot_preview.setStyleSheet("""
            QLabel {
                background-color: #263238;
                border: 2px solid #37474f;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        self.screenshot_preview.setMaximumHeight(150)
        self.screenshot_preview.setScaledContents(False)
        screenshot_preview_layout.addWidget(self.screenshot_preview)
        
        self.screenshot_preview_container.hide()
        main_layout.addWidget(self.screenshot_preview_container)
        
        # === Панель ввода ===
        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)
        
        # Кнопка скриншота
        self.screenshot_btn = QPushButton("📷")
        self.screenshot_btn.setObjectName("screenshotButton")
        self.screenshot_btn.setToolTip(t("take_screenshot"))
        self.screenshot_btn.clicked.connect(self._on_screenshot_click)
        input_layout.addWidget(self.screenshot_btn)
        
        # Поле ввода
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText(t("enter_question"))
        self.input_field.returnPressed.connect(self._on_send_message)
        input_layout.addWidget(self.input_field, 1)
        
        # Кнопка отправки
        self.send_btn = QPushButton(t("send"))
        self.send_btn.setObjectName("sendButton")
        self.send_btn.clicked.connect(self._on_send_message)
        input_layout.addWidget(self.send_btn)
        
        main_layout.addLayout(input_layout)
        
        # === Нижняя панель ===
        footer_layout = QHBoxLayout()
        
        # Кнопка "Отправить отзыв" (ссылка на ТГ)
        self.feedback_btn = QPushButton(t("send_feedback"))
        self.feedback_btn.setObjectName("feedbackButton")
        self.feedback_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.feedback_btn.clicked.connect(self._on_feedback_click)
        footer_layout.addWidget(self.feedback_btn)
        
        footer_layout.addStretch()
        
        # Выбор модели
        self.model_label = QLabel(t("model"))
        self.model_label.setStyleSheet("color: #6c757d; font-size: 12px;")
        footer_layout.addWidget(self.model_label)
        
        self.model_combo = StyledModelComboBox()
        self.model_combo.setObjectName("modelCombo")
        self.model_combo.setMinimumWidth(200)
        self._populate_models()
        self.model_combo.currentIndexChanged.connect(self._on_model_changed)
        footer_layout.addWidget(self.model_combo)
        
        # Кнопка настроек
        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setObjectName("settingsButton")
        self.settings_btn.setFixedSize(30, 30)
        self.settings_btn.setToolTip(t("settings"))
        self.settings_btn.clicked.connect(self._open_settings)
        footer_layout.addWidget(self.settings_btn)
        
        # Провайдер и баланс (кликабельный, после шестерёнки)
        self.provider_balance_label = QLabel("")
        self.provider_balance_label.setStyleSheet("""
            QLabel {
                color: #6c757d;
                font-size: 11px;
            }
            QLabel:hover {
                color: #ff6b6b;
            }
        """)
        self.provider_balance_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.provider_balance_label.mousePressEvent = self._on_balance_click
        footer_layout.addWidget(self.provider_balance_label)
        
        # Индикатор скриншота
        self.screenshot_indicator = QLabel("")
        self.screenshot_indicator.setStyleSheet("color: #4fc3f7; font-size: 12px;")
        footer_layout.addWidget(self.screenshot_indicator)
        
        # Грип для изменения размера (30x30 как шестеренка)
        grip_container = QWidget()
        grip_container.setFixedSize(30, 30)
        grip_container.setToolTip("Изменить размер")
        grip_container.setCursor(Qt.CursorShape.SizeFDiagCursor)
        
        # Визуальный индикатор
        grip_label = QLabel("⤡", grip_container)
        grip_label.setStyleSheet("color: #ffffff; font-size: 20px;")
        grip_label.setGeometry(0, 0, 30, 30)
        grip_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Функциональный грип поверх
        size_grip = QSizeGrip(grip_container)
        size_grip.setGeometry(0, 0, 30, 30)
        
        footer_layout.addWidget(grip_container)
        
        main_layout.addLayout(footer_layout)
    
    def _apply_styles(self):
        """Применение стилей"""
        self.setStyleSheet(DARK_THEME)
        
        # Инициализация чата с CSS
        self._update_chat_display()
        
        # Показываем инструкцию если нужно
        self._update_setup_message()
    
    def _update_setup_message(self):
        """Показать/скрыть инструкцию по настройке в области чата"""
        settings = self._load_settings()
        api_key = settings.get("api_key", "")
        models = settings.get("models", [])
        
        # Если нет API ключа или нет моделей и (чат пуст или показана инструкция) — показываем инструкцию
        if not api_key or not models:
            if not self._chat_history_html or self._showing_setup_instruction:
                self._show_setup_instruction()
        
        # Обновляем placeholder поля ввода
        self.input_field.setPlaceholderText(t("enter_question"))
    
    def _show_setup_instruction(self):
        """Показать инструкцию по настройке в области чата"""
        lang = Localization.get_language()
        
        if lang == "ru":
            # Для русского интерфейса - AITunnel (оплата в рублях)
            html = '''
            <div style="text-align: center; padding: 30px 20px;">
                <div style="font-size: 48px; margin-bottom: 15px;">⚙️</div>
                <div style="font-size: 20px; color: #ffffff; margin-bottom: 12px;">
                    <strong>Добро пожаловать в AI Helper!</strong>
                </div>
                <div style="font-size: 15px; color: #aaaaaa; text-align: left; display: inline-block; line-height: 1.6;">
                    <strong style="color: #4fc3f7;">Для начала работы:</strong><br>
                    1. Зарегистрируйтесь на <a href="https://aitunnel.ru" style="color: #4fc3f7;">aitunnel.ru</a><br>
                    2. Откройте настройки (⚙️) и введите API-ключ<br><br>
                    <strong style="color: #ff9800;">Выбор провайдера:</strong><br>
                    • <strong>AITunnel</strong> — оплата в рублях, бесплатных моделей нет<br>
                    • <strong>OpenRouter</strong> — оплата в $, есть бесплатные модели<br><br>
                    <span style="color: #888;">Добавьте модели с поддержкой Vision для работы со скриншотами</span>
                </div>
            </div>
            '''
        else:
            # Для английского - OpenRouter
            html = '''
            <div style="text-align: center; padding: 30px 20px;">
                <div style="font-size: 48px; margin-bottom: 15px;">⚙️</div>
                <div style="font-size: 20px; color: #ffffff; margin-bottom: 12px;">
                    <strong>Welcome to AI Helper!</strong>
                </div>
                <div style="font-size: 15px; color: #aaaaaa; text-align: left; display: inline-block; line-height: 1.6;">
                    <strong style="color: #4fc3f7;">To get started:</strong><br>
                    1. Sign up at <a href="https://openrouter.ai/keys" style="color: #4fc3f7;">openrouter.ai/keys</a><br>
                    2. Open settings (⚙️) and enter your API key<br><br>
                    <strong style="color: #ff9800;">Provider choice:</strong><br>
                    • <strong>OpenRouter</strong> — pay in $, has FREE models<br>
                    • <strong>AITunnel</strong> — pay in ₽, no free models<br><br>
                    <span style="color: #888;">Add Vision models to work with screenshots</span>
                </div>
            </div>
            '''
        
        self._chat_history_html = html
        self._showing_setup_instruction = True
        self._update_chat_display()
    
    def _update_chat_display(self):
        """Обновить отображение чата"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            {CHAT_MESSAGE_CSS}
        </head>
        <body>
            {self._chat_history_html}
        </body>
        </html>
        """
        self.chat_display.setHtml(html)
        
        # Прокрутка вниз
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.chat_display.setTextCursor(cursor)
    
    def _add_message(self, role: str, text: str):
        """Добавить сообщение в чат"""
        # Если была показана инструкция — очищаем
        if self._showing_setup_instruction:
            self._chat_history_html = ""
            self._showing_setup_instruction = False
        
        # Конвертируем markdown в HTML
        html_text = self._markdown_to_html(text)
        
        if role == "user":
            message_html = f'''
            <div class="message user-message">
                <div class="message-header">Вы</div>
                <div class="message-content">{html_text}</div>
            </div>
            '''
        else:
            message_html = f'''
            <div class="message assistant-message">
                <div class="message-header">AI Helper</div>
                <div class="message-content">{html_text}</div>
            </div>
            '''
        
        self._chat_history_html += message_html
        self._update_chat_display()
    
    def _markdown_to_html(self, text: str) -> str:
        """Простая конвертация markdown в HTML"""
        # Экранируем HTML
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        # Изображения ![alt](url)
        text = re.sub(
            r'!\[([^\]]*)\]\(([^)]+)\)',
            r'<img src="\2" alt="\1" />',
            text
        )
        
        # Ссылки [text](url)
        text = re.sub(
            r'\[([^\]]+)\]\(([^)]+)\)',
            r'<a href="\2">\1</a>',
            text
        )
        
        # Жирный текст **text**
        text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
        
        # Курсив *text*
        text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)
        
        # Код ```code```
        text = re.sub(
            r'```(\w*)\n?([\s\S]*?)```',
            r'<pre><code>\2</code></pre>',
            text
        )
        
        # Инлайн код `code`
        text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
        
        # Переносы строк
        text = text.replace("\n", "<br>")
        
        return text
    
    def _handle_link_click(self, url: QUrl):
        """Обработка клика по ссылке"""
        url_str = url.toString()
        # API провайдеры и GitHub открываем во внешнем браузере
        if 'openrouter.ai' in url_str or 'aitunnel.ru' in url_str or 'github.com' in url_str:
            QDesktopServices.openUrl(url)
        else:
            dialog = WebDialog(self, url_str)
            dialog.exec()
    
    def _on_send_message(self):
        """Отправка сообщения"""
        text = self.input_field.text().strip()
        if not text:
            return
        
        # Очищаем поле ввода
        self.input_field.clear()
        
        # Показываем сообщение пользователя
        display_text = text
        if self._current_screenshot_context:
            display_text = f"📷 [Со скриншотом]\n{text}"
        self._add_message("user", display_text)
        
        # Блокируем UI
        self._set_input_enabled(False)
        
        # Запускаем запрос в фоне
        if self.gpt_client:
            # Добавляем контекст активного окна к сообщению
            message_with_context = text
            if self._current_app_context:
                message_with_context = f"[Активное окно: {self._current_app_context}]\n{text}"
            
            self._worker = AIWorker(
                self.gpt_client,
                message_with_context,
                self._current_screenshot_context,
                self._current_screenshot_bytes  # Передаём байты изображения
            )
            self._worker.response_ready.connect(self._on_response)
            self._worker.error_occurred.connect(self._on_error)
            self._worker.start()
        else:
            self._add_message("assistant", "❌ AI клиент не инициализирован. Проверьте config.py")
            self._set_input_enabled(True)
        
        # Сбрасываем контекст скриншота
        self._remove_screenshot()
    
    def _on_response(self, response: str):
        """Получен ответ от AI"""
        self._add_message("assistant", response)
        self._set_input_enabled(True)
        # Обновляем баланс после ответа
        self._update_balance()
    
    def _on_error(self, error: str):
        """Произошла ошибка"""
        self._add_message("assistant", f"❌ Ошибка: {error}")
        self._set_input_enabled(True)
    
    def _set_input_enabled(self, enabled: bool):
        """Включить/выключить UI"""
        self.input_field.setEnabled(enabled)
        self.send_btn.setEnabled(enabled)
        self.screenshot_btn.setEnabled(enabled)
        
        if not enabled:
            self.send_btn.setText("⏳")
        else:
            self.send_btn.setText("Отправить")
    
    def _on_screenshot_click(self):
        """Клик по кнопке скриншота"""
        self.screenshot_requested.emit()
    
    def set_screenshot_context(self, context: str, image_data: bytes = None):
        """Установить контекст скриншота"""
        self._current_screenshot_context = context
        
        if context and image_data:
            # Сохраняем байты изображения
            self._current_screenshot_bytes = image_data
            
            # Создаём превью
            pixmap = QPixmap()
            pixmap.loadFromData(QByteArray(image_data))
            
            # Скейлим до разумного размера
            if pixmap.width() > 400:
                pixmap = pixmap.scaledToWidth(400, Qt.TransformationMode.SmoothTransformation)
            
            self._current_screenshot_image = pixmap
            self.screenshot_preview.setPixmap(pixmap)
            self.screenshot_preview_container.show()
            self.screenshot_indicator.setText(t("screenshot_attached"))
        else:
            self._remove_screenshot()
    
    def _remove_screenshot(self):
        """Удалить скриншот"""
        self._current_screenshot_context = ""
        self._current_screenshot_image = None
        self._current_screenshot_bytes = None
        self.screenshot_preview.clear()
        self.screenshot_preview_container.hide()
        self.screenshot_indicator.setText("")
    
    def _update_context(self):
        """Обновить контекст (игра/приложение)"""
        if not self.context_detector:
            return
        
        # Если окно видимо - скрываем, определяем контекст, показываем
        if self.isVisible():
            self.hide()
            QTimer.singleShot(150, self._do_update_context)
        else:
            self._do_update_context()
    
    def _do_update_context(self):
        """Фактически обновить контекст"""
        context = self.context_detector.get_active_window_context()
        if context:
            self.context_label.setText(f"{context.app_name}")
            self._current_app_context = context.app_name
            
            # Обновляем системный промпт
            if self.gpt_client:
                game_name = context.app_name if context.app_type == "game" else None
                self.gpt_client.update_context(game_name=game_name)
        else:
            self.context_label.setText(t("not_detected"))
            self._current_app_context = ""
        
        # Показываем окно обратно
        if not self.isVisible():
            self.show()
            self._force_focus_from_game()
            self.input_field.setFocus()
    
    def _clear_chat(self):
        """Очистить чат"""
        self._chat_history_html = ""
        self._showing_setup_instruction = False
        self._update_chat_display()
        self._update_setup_message()  # Показать инструкцию если нужно
        
        if self.gpt_client:
            self.gpt_client.clear_history()
            self._update_context()  # Восстанавливаем системный промпт
    
    def toggle_visibility(self):
        """Переключить видимость окна"""
        if self.isVisible():
            self.hide()
        else:
            # Сначала определяем контекст (пока оверлей скрыт)
            if self.context_detector:
                context = self.context_detector.get_active_window_context()
                if context:
                    self.context_label.setText(f"{context.app_name}")
                    self._current_app_context = context.app_name
                    if self.gpt_client:
                        game_name = context.app_name if context.app_type == "game" else None
                        self.gpt_client.update_context(game_name=game_name)
                else:
                    self.context_label.setText(t("not_detected"))
                    self._current_app_context = ""
            
            # Обновляем баланс при показе
            self._update_balance()
            
            # Показываем окно
            self.show()
            self._force_focus_from_game()
            self.input_field.setFocus()
    
    def _update_balance(self):
        """Обновить баланс в фоне"""
        if self.gpt_client:
            self._balance_worker = BalanceWorker(self.gpt_client)
            self._balance_worker.balance_ready.connect(self._on_balance_ready)
            self._balance_worker.start()
    
    def _on_balance_ready(self, data: dict):
        """Обработчик получения баланса"""
        provider = data.get("provider", "")
        balance = data.get("balance")
        currency = data.get("currency", "")
        
        if balance is not None:
            # Форматируем баланс
            if balance >= 100:
                balance_str = f"{balance:.0f}"
            else:
                balance_str = f"{balance:.2f}"
            self.provider_balance_label.setText(f"{provider} • {balance_str}{currency}")
        else:
            self.provider_balance_label.setText(provider)
    
    def _on_balance_click(self, event):
        """Клик по балансу - открыть страницу трат"""
        settings = self._load_settings()
        provider = settings.get("api_provider", "openrouter")
        
        if provider == "aitunnel":
            url = "https://aitunnel.ru/panel/stats"
        else:
            url = "https://openrouter.ai/activity"
        
        QDesktopServices.openUrl(QUrl(url))
    
    def _on_feedback_click(self):
        """Клик по кнопке отзыва - открыть Телеграм"""
        QDesktopServices.openUrl(QUrl("https://t.me/megavolk"))
    
    def _on_version_click(self, event):
        """Клик по версии - открыть GitHub репозиторий или страницу релизов"""
        if self._new_version_url:
            QDesktopServices.openUrl(QUrl(self._new_version_url))
        else:
            QDesktopServices.openUrl(QUrl(f"https://github.com/{GITHUB_REPO}"))
    
    def _check_for_updates(self):
        """Проверить обновления в фоне"""
        self._update_worker = UpdateCheckerWorker()
        self._update_worker.update_available.connect(self._on_update_available)
        self._update_worker.start()
    
    def _on_update_available(self, new_version: str, release_url: str):
        """Обработчик: доступно обновление"""
        self._new_version = new_version
        self._new_version_url = release_url
        
        # Меняем цвет версии на красный
        self.version_label.setText(f"v{get_current_version()} → v{new_version}")
        self.version_label.setStyleSheet("""
            QLabel {
                color: #ff6b6b;
                font-size: 10px;
                font-weight: bold;
            }
            QLabel:hover {
                color: #ff4444;
            }
        """)
        self.version_label.setToolTip(f"Доступна новая версия! Нажмите для загрузки")
        
        # Показываем сообщение в чате
        lang = Localization.get_language()
        if lang == "ru":
            message = f'''🆕 <strong>Доступна новая версия {new_version}!</strong><br>
            <a href="{release_url}" style="color: #4fc3f7;">Скачать обновление</a>'''
        else:
            message = f'''🆕 <strong>New version {new_version} available!</strong><br>
            <a href="{release_url}" style="color: #4fc3f7;">Download update</a>'''
        
        # Добавляем как системное сообщение
        self._add_system_message(message)
    
    def _add_system_message(self, html: str):
        """Добавить системное сообщение в чат"""
        # Если была показана инструкция — не перезаписываем
        if self._showing_setup_instruction:
            return
        
        message_html = f'''
        <div class="message system-message" style="background-color: #2d3a4a; border-left: 3px solid #4fc3f7;">
            <div class="message-content" style="padding: 10px;">{html}</div>
        </div>
        '''
        
        self._chat_history_html += message_html
        self._update_chat_display()
    
    def keyPressEvent(self, event):
        """Обработка нажатий клавиш"""
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)
    
    # === Перетаскивание окна ===
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, '_drag_pos'):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
    
    def resizeEvent(self, event):
        """Обработка изменения размера окна"""
        super().resizeEvent(event)
        self._position_chat_elements()
    
    def showEvent(self, event):
        """При показе окна"""
        super().showEvent(event)
        # Отложенное позиционирование после layout
        QTimer.singleShot(0, self._position_chat_elements)
    
    def _position_chat_elements(self):
        """Позиционировать элементы поверх чата"""
        if hasattr(self, '_chat_inner') and hasattr(self, 'chat_display') and hasattr(self, 'clear_btn'):
            # Растягиваем chat_display на весь контейнер
            self.chat_display.setGeometry(0, 0, self._chat_inner.width(), self._chat_inner.height())
            
            # Позиционируем кнопку очистки в правом нижнем углу
            btn_width = self.clear_btn.sizeHint().width()
            btn_height = self.clear_btn.sizeHint().height()
            margin = 10
            self.clear_btn.setGeometry(
                self._chat_inner.width() - btn_width - margin,
                self._chat_inner.height() - btn_height - margin,
                btn_width,
                btn_height
            )
            self.clear_btn.raise_()
    
    # === Выбор модели ===
    
    def _get_settings_path(self):
        """Получить путь к файлу настроек"""
        # Определяем базовый путь (для PyInstaller и dev-режима)
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(base_path, "settings.json")
    
    def _load_settings(self):
        """Загрузить настройки"""
        try:
            with open(self._get_settings_path(), 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def _save_settings(self, settings):
        """Сохранить настройки"""
        try:
            with open(self._get_settings_path(), 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2)
        except:
            pass
    
    def _get_models_list(self):
        """Получить список моделей (из settings или config в зависимости от провайдера)"""
        settings = self._load_settings()
        models = settings.get("models", [])
        
        # Если в настройках пусто - используем дефолтные в зависимости от провайдера
        if not models:
            provider = settings.get("api_provider", "openrouter")
            if provider == "aitunnel":
                models = getattr(config, 'AITUNNEL_MODELS', [])
            else:
                models = getattr(config, 'OPENROUTER_MODELS', [])
        
        return models
    
    def _populate_models(self):
        """Заполнить список моделей"""
        models = self._get_models_list()
        
        # Загружаем сохранённую модель
        settings = self._load_settings()
        saved_model = settings.get("selected_model", "")
        
        for model_id, display_name in models:
            self.model_combo.addItem(display_name, model_id)
        
        # Устанавливаем сохранённую модель
        if saved_model:
            for i in range(self.model_combo.count()):
                if self.model_combo.itemData(i) == saved_model:
                    self.model_combo.setCurrentIndex(i)
                    if self.gpt_client:
                        self.gpt_client.set_model(saved_model)
                    break
    
    def _refresh_models_combo(self):
        """Обновить комбобокс моделей"""
        # Сохраняем текущую модель
        current_model = self.model_combo.currentData()
        
        # Очищаем и заполняем заново
        self.model_combo.clear()
        models = self._get_models_list()
        
        for model_id, display_name in models:
            self.model_combo.addItem(display_name, model_id)
        
        # Восстанавливаем выбор
        if current_model:
            for i in range(self.model_combo.count()):
                if self.model_combo.itemData(i) == current_model:
                    self.model_combo.setCurrentIndex(i)
                    break
    
    def _on_model_changed(self, index: int):
        """Обработчик смены модели"""
        if index < 0:
            return
        
        model_id = self.model_combo.itemData(index)
        if model_id and self.gpt_client:
            self.gpt_client.set_model(model_id)
            # Сохраняем выбор
            settings = self._load_settings()
            settings["selected_model"] = model_id
            self._save_settings(settings)
    
    def _open_settings(self):
        """Открыть диалог настроек"""
        current_settings = self._load_settings()
        
        # Добавляем текущие горячие клавиши из config если их нет в settings
        if "hotkey_overlay" not in current_settings:
            current_settings["hotkey_overlay"] = getattr(config, 'HOTKEY_TOGGLE_OVERLAY', 'Insert')
        if "hotkey_screenshot" not in current_settings:
            current_settings["hotkey_screenshot"] = getattr(config, 'HOTKEY_SCREENSHOT', 'Home')
        if "api_key" not in current_settings:
            current_settings["api_key"] = getattr(config, 'OPENROUTER_API_KEY', '')
        
        # Добавляем текущие модели (в зависимости от провайдера)
        if "models" not in current_settings or not current_settings["models"]:
            provider = current_settings.get("api_provider", "openrouter")
            if provider == "aitunnel":
                current_settings["models"] = getattr(config, 'AITUNNEL_MODELS', [])
            else:
                current_settings["models"] = getattr(config, 'OPENROUTER_MODELS', [])
        
        # Добавляем текущее состояние автозапуска
        if self.autostart_checker:
            current_settings["autostart"] = self.autostart_checker()
        
        dialog = SettingsDialog(self, current_settings)
        dialog.settings_saved.connect(self._on_settings_saved)
        dialog.exec()
    
    def _on_settings_saved(self, new_settings: dict):
        """Обработчик сохранения настроек"""
        self._save_settings(new_settings)
        
        # Перезагружаем настройки клиента (провайдер, ключ, base_url)
        if self.gpt_client:
            self.gpt_client.reload_settings()
        
        # Обновляем список моделей
        if "models" in new_settings:
            self._refresh_models_combo()
        
        # Обновляем горячие клавиши
        hotkey_overlay = new_settings.get("hotkey_overlay", "Insert")
        hotkey_screenshot = new_settings.get("hotkey_screenshot", "Home")
        self.hotkeys_changed.emit(hotkey_overlay, hotkey_screenshot)
        
        # Обновляем автозапуск
        if "autostart" in new_settings:
            self.autostart_changed.emit(new_settings["autostart"])
        
        # Очищаем чат и обновляем инструкцию
        self._chat_history_html = ""
        self._showing_setup_instruction = False
        self._update_chat_display()
        self._update_setup_message()
        
        # Очищаем историю клиента
        if self.gpt_client:
            self.gpt_client.clear_history()
        
        # Обновляем баланс
        self._update_balance()
    
    # === Локализация ===
    
    def _load_language(self):
        """Загрузить язык из настроек"""
        settings = self._load_settings()
        lang = settings.get("language", "ru")
        Localization.set_language(lang)
    
    def _toggle_language(self):
        """Переключить язык"""
        Localization.toggle_language()
        self._update_lang_button()
        
        # Сохраняем выбор
        settings = self._load_settings()
        settings["language"] = Localization.get_language()
        self._save_settings(settings)
    
    def _update_lang_button(self):
        """Обновить текст кнопки языка"""
        lang = Localization.get_language()
        if lang == "ru":
            self.lang_btn.setText("RU|en")
        else:
            self.lang_btn.setText("ru|EN")
    
    def _update_ui_texts(self):
        """Обновить все тексты UI при смене языка"""
        self._update_lang_button()
        
        # Обновляем название
        self.title_label.setText(t("app_name"))
        self.setWindowTitle(t("app_name"))
        
        # Обновляем тексты
        self.refresh_context_btn.setToolTip(t("refresh_context"))
        self.chat_display.setPlaceholderText(t("ask_question"))
        self.preview_label.setText(t("screenshot_preview"))
        self.screenshot_btn.setToolTip(t("take_screenshot"))
        self._update_setup_message()  # Учитываем состояние настроек
        self.send_btn.setText(t("send"))
        self.clear_btn.setText(t("clear_chat"))
        self.feedback_btn.setText(t("send_feedback"))
        self.model_label.setText(t("model"))
        self.settings_btn.setToolTip(t("settings"))
        
        # Обновляем контекст если не определён
        if self.context_label.text() in ("Не определено", "Not detected"):
            self.context_label.setText(t("not_detected"))
        
        # Обновляем индикатор скриншота
        if self._current_screenshot_bytes:
            self.screenshot_indicator.setText(t("screenshot_attached"))
