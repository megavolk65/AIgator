"""
Диалог настроек приложения
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QGroupBox, QFormLayout,
    QKeySequenceEdit, QMessageBox, QScrollArea,
    QInputDialog, QCheckBox, QWidget, QFrame, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from PyQt6.QtGui import QKeySequence, QDesktopServices
import json
import os
import sys

from src.localization import t


class SettingsDialog(QDialog):
    """Диалог настроек"""
    
    settings_saved = pyqtSignal(dict)  # Сигнал при сохранении настроек
    
    def __init__(self, parent=None, current_settings=None):
        super().__init__(parent)
        self.current_settings = current_settings or {}
        self._init_ui()
        self._load_current_settings()
    
    def _init_ui(self):
        """Инициализация интерфейса"""
        self.setWindowTitle(t("settings"))
        self.setFixedSize(500, 550)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # === API провайдер ===
        api_group = QGroupBox("API")
        api_layout = QVBoxLayout(api_group)
        
        # Выбор провайдера
        provider_layout = QHBoxLayout()
        provider_layout.addWidget(QLabel(t("api_provider") + ":"))
        
        self.provider_combo = QComboBox()
        self.provider_combo.addItem(t("provider_openrouter"), "openrouter")
        self.provider_combo.addItem(t("provider_aitunnel"), "aitunnel")
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        provider_layout.addWidget(self.provider_combo, 1)
        
        api_layout.addLayout(provider_layout)
        
        # API ключ
        key_layout = QHBoxLayout()
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("sk-or-v1-...")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.show_key_btn = QPushButton("👁")
        self.show_key_btn.setFixedSize(40, 36)
        self.show_key_btn.setCheckable(True)
        self.show_key_btn.setToolTip(t("show_hide"))
        self.show_key_btn.setStyleSheet("font-size: 18px; padding: 0px;")
        self.show_key_btn.toggled.connect(self._toggle_key_visibility)
        
        key_layout.addWidget(QLabel(t("api_key")))
        key_layout.addWidget(self.api_key_input, 1)
        key_layout.addWidget(self.show_key_btn)
        
        api_layout.addLayout(key_layout)
        
        layout.addWidget(api_group)
        
        # === Модели ===
        models_group = QGroupBox(t("models"))
        models_layout = QVBoxLayout(models_group)
        
        # Ссылка на OpenRouter + кнопка добавить
        header_layout = QHBoxLayout()
        link_label = QLabel(f'<a href="https://openrouter.ai/models?fmt=cards&input_modalities=text%2Cimage&modality=text%2Bimage-%3Etext" style="color: #4fc3f7;">{t("models_catalog")}</a>')
        link_label.setOpenExternalLinks(True)
        header_layout.addWidget(link_label)
        header_layout.addStretch()
        
        add_model_btn = QPushButton(t("add"))
        add_model_btn.clicked.connect(self._add_model)
        header_layout.addWidget(add_model_btn)
        
        models_layout.addLayout(header_layout)
        
        # Список моделей (через QScrollArea)
        self.models_scroll = QScrollArea()
        self.models_scroll.setWidgetResizable(True)
        self.models_scroll.setMinimumHeight(120)
        self.models_scroll.setMaximumHeight(150)
        self.models_scroll.setStyleSheet("""
            QScrollArea {
                background-color: #2a2a4a;
                border: 1px solid #3a3a5a;
                border-radius: 5px;
            }
        """)
        
        self.models_container = QWidget()
        self.models_container.setStyleSheet("background-color: #2a2a4a;")
        self.models_layout_inner = QVBoxLayout(self.models_container)
        self.models_layout_inner.setContentsMargins(5, 5, 5, 5)
        self.models_layout_inner.setSpacing(3)
        self.models_layout_inner.addStretch()  # Для прижатия элементов вверх
        
        self.models_scroll.setWidget(self.models_container)
        models_layout.addWidget(self.models_scroll)
        
        layout.addWidget(models_group)
        
        # === Горячие клавиши ===
        hotkeys_group = QGroupBox(t("hotkeys"))
        hotkeys_layout = QFormLayout(hotkeys_group)
        
        self.hotkey_overlay = QKeySequenceEdit()
        self.hotkey_overlay.setFixedWidth(150)
        hotkeys_layout.addRow(t("open_close"), self.hotkey_overlay)
        
        self.hotkey_screenshot = QKeySequenceEdit()
        self.hotkey_screenshot.setFixedWidth(150)
        hotkeys_layout.addRow(t("screenshot"), self.hotkey_screenshot)
        
        layout.addWidget(hotkeys_group)
        
        # === Автозапуск ===
        self.autostart_checkbox = QCheckBox(t("autostart"))
        layout.addWidget(self.autostart_checkbox)
        
        # === Кнопки ===
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        self.cancel_btn = QPushButton(t("cancel"))
        self.cancel_btn.clicked.connect(self.reject)
        
        self.save_btn = QPushButton(t("save"))
        self.save_btn.clicked.connect(self._save_settings)
        self.save_btn.setDefault(True)
        
        buttons_layout.addWidget(self.cancel_btn)
        buttons_layout.addWidget(self.save_btn)
        
        layout.addLayout(buttons_layout)
        
        # Стили
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a2e;
                color: #ffffff;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #3a3a5a;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLineEdit, QKeySequenceEdit {
                background-color: #2a2a4a;
                border: 1px solid #3a3a5a;
                border-radius: 5px;
                padding: 8px;
                color: #ffffff;
            }
            QLineEdit:focus, QKeySequenceEdit:focus {
                border-color: #667eea;
            }
            QLabel {
                color: #cccccc;
            }
            QPushButton {
                background-color: #3a3a5a;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #4a4a6a;
            }
            QPushButton:pressed {
                background-color: #2a2a4a;
            }
            QPushButton#saveBtn {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }
        """)
        
        self.save_btn.setObjectName("saveBtn")
    
    def _toggle_key_visibility(self, checked):
        """Переключить видимость API ключа"""
        if checked:
            self.api_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_key_btn.setText("🔒")
        else:
            self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_key_btn.setText("👁")
    
    def _on_provider_changed(self, index):
        """Обработчик смены провайдера"""
        provider = self.provider_combo.currentData()
        if provider == "openrouter":
            self.api_key_input.setPlaceholderText("sk-or-v1-...")
        else:
            self.api_key_input.setPlaceholderText("sk-aitunnel-...")
    
    def _load_current_settings(self):
        """Загрузить текущие настройки в поля"""
        # API провайдер
        provider = self.current_settings.get("api_provider", "openrouter")
        index = self.provider_combo.findData(provider)
        if index >= 0:
            self.provider_combo.setCurrentIndex(index)
        
        # API ключ
        api_key = self.current_settings.get("api_key", "")
        self.api_key_input.setText(api_key)
        
        # Модели
        models = self.current_settings.get("models", [])
        for model_id, display_name in models:
            self._add_model_item(model_id, display_name)
        
        # Горячие клавиши
        hotkey_overlay = self.current_settings.get("hotkey_overlay", "Insert")
        hotkey_screenshot = self.current_settings.get("hotkey_screenshot", "Home")
        
        self.hotkey_overlay.setKeySequence(QKeySequence(hotkey_overlay))
        self.hotkey_screenshot.setKeySequence(QKeySequence(hotkey_screenshot))
        
        # Автозапуск
        autostart = self.current_settings.get("autostart", False)
        self.autostart_checkbox.setChecked(autostart)
    
    def _add_model_item(self, model_id: str, display_name: str):
        """Добавить элемент модели с кнопкой удаления"""
        # Создаём виджет-строку
        row_widget = QFrame()
        row_widget.setProperty("model_id", model_id)
        row_widget.setStyleSheet("""
            QFrame {
                background-color: #3a3a5a;
                border-radius: 4px;
            }
        """)
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(8, 4, 4, 4)
        row_layout.setSpacing(5)
        
        label = QLabel(display_name)
        label.setProperty("display_name", display_name)
        label.setStyleSheet("color: #ffffff; background: transparent;")
        row_layout.addWidget(label, 1)
        
        remove_btn = QPushButton()
        remove_btn.setText("X")
        remove_btn.setFixedSize(26, 26)
        remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #5a5a7a;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
                padding: 0px;
                margin: 0px;
            }
            QPushButton:hover {
                background-color: #ff6b6b;
                color: #ffffff;
            }
        """)
        remove_btn.clicked.connect(lambda: self._remove_model_row(row_widget))
        row_layout.addWidget(remove_btn)
        
        # Вставляем перед stretch
        count = self.models_layout_inner.count()
        self.models_layout_inner.insertWidget(count - 1, row_widget)
    
    def _model_id_to_display_name(self, model_id: str) -> str:
        """Сгенерировать display_name из model_id"""
        # google/gemini-2.0-flash -> GOOGLE: Gemini 2.0 Flash
        if "/" in model_id:
            provider, model = model_id.split("/", 1)
            # Убираем суффиксы вроде :free, :online
            model = model.split(":")[0]
            # Форматируем
            model_name = model.replace("-", " ").title()
            return f"{provider.upper()}: {model_name}"
        return model_id.replace("-", " ").title()
    
    def _add_model(self):
        """Добавить модель"""
        model_id, ok = QInputDialog.getText(
            self, 
            t("add_model"),
            t("model_id_prompt")
        )
        if not ok or not model_id.strip():
            return
        
        model_id = model_id.strip()
        display_name = self._model_id_to_display_name(model_id)
        self._add_model_item(model_id, display_name)
    
    def _remove_model_row(self, row_widget: QFrame):
        """Удалить модель"""
        self.models_layout_inner.removeWidget(row_widget)
        row_widget.deleteLater()
    
    def _save_settings(self):
        """Сохранить настройки"""
        # Получаем провайдер и ключ
        api_provider = self.provider_combo.currentData()
        api_key = self.api_key_input.text().strip()
        
        # Мягкая валидация API ключа
        if api_key:
            if api_provider == "openrouter" and not api_key.startswith("sk-or-"):
                QMessageBox.warning(
                    self, 
                    t("error").replace("❌ ", ""), 
                    "OpenRouter API key should start with 'sk-or-'"
                )
                return
            elif api_provider == "aitunnel" and not api_key.startswith("sk-aitunnel-"):
                QMessageBox.warning(
                    self, 
                    t("error").replace("❌ ", ""), 
                    "AITunnel API key should start with 'sk-aitunnel-'"
                )
                return
        
        # Получаем модели
        models = []
        for i in range(self.models_layout_inner.count()):
            widget = self.models_layout_inner.itemAt(i).widget()
            if widget and isinstance(widget, QFrame):
                model_id = widget.property("model_id")
                label = widget.findChild(QLabel)
                display_name = label.property("display_name") if label else model_id
                if model_id:
                    models.append((model_id, display_name))
        
        # Получаем горячие клавиши
        hotkey_overlay = self.hotkey_overlay.keySequence().toString()
        hotkey_screenshot = self.hotkey_screenshot.keySequence().toString()
        
        if not hotkey_overlay:
            hotkey_overlay = "Insert"
        if not hotkey_screenshot:
            hotkey_screenshot = "Home"
        
        # Автозапуск
        autostart = self.autostart_checkbox.isChecked()
        
        # Формируем настройки
        new_settings = {
            **self.current_settings,
            "api_provider": api_provider,
            "api_key": api_key,
            "models": models,
            "hotkey_overlay": hotkey_overlay,
            "hotkey_screenshot": hotkey_screenshot,
            "autostart": autostart
        }
        
        # Отправляем сигнал
        self.settings_saved.emit(new_settings)
        self.accept()
    
    def get_settings(self):
        """Получить текущие настройки из полей"""
        return {
            "api_key": self.api_key_input.text().strip(),
            "hotkey_overlay": self.hotkey_overlay.keySequence().toString() or "Insert",
            "hotkey_screenshot": self.hotkey_screenshot.keySequence().toString() or "Home"
        }
