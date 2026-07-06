"""
Диалог настроек приложения
"""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QGroupBox,
    QFormLayout,
    QKeySequenceEdit,
    QMessageBox,
    QScrollArea,
    QInputDialog,
    QCheckBox,
    QWidget,
    QFrame,
    QComboBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl, QThread
from PyQt6.QtGui import QKeySequence, QDesktopServices
import json
import os
import sys
import threading

from src.localization import t


class OAuthWorker(QThread):
    """Фоновый поток OAuth PKCE подключения OpenRouter"""

    success = pyqtSignal(str, list)  # api_key, [(model_id, display_name), ...]
    failed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._stop_event = threading.Event()

    def stop(self):
        """Прервать ожидание (закрытие диалога)"""
        self._stop_event.set()

    def run(self):
        try:
            from src.ai.openrouter_oauth import perform_oauth, pick_free_models

            key = perform_oauth(stop_event=self._stop_event)
            models = pick_free_models()
            self.success.emit(key, models)
        except InterruptedError:
            pass  # отмена — молча
        except Exception as e:
            self.failed.emit(str(e))


class SettingsDialog(QDialog):
    """Диалог настроек"""

    settings_saved = pyqtSignal(dict)  # Сигнал при сохранении настроек

    def __init__(self, parent=None, current_settings=None):
        super().__init__(parent)
        self.current_settings = current_settings or {}

        # Ключи по-провайдерно (легаси api_key приписываем текущему провайдеру)
        self._provider_keys = dict(self.current_settings.get("api_keys") or {})
        legacy_key = self.current_settings.get("api_key", "")
        legacy_provider = self.current_settings.get("api_provider", "openrouter")
        if legacy_key and not self._provider_keys.get(legacy_provider):
            self._provider_keys[legacy_provider] = legacy_key
        self._active_key_provider = None  # чей ключ сейчас в поле

        self._init_ui()
        self._load_current_settings()

    def _init_ui(self):
        """Инициализация интерфейса"""
        self.setWindowTitle(t("settings"))
        self.setFixedSize(500, 660)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )

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
        self.provider_combo.addItem(t("provider_routerai"), "routerai")
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

        # Кнопка OAuth-подключения OpenRouter (видна только для OpenRouter)
        self.oauth_btn = QPushButton(t("connect_openrouter"))
        self.oauth_btn.setToolTip(t("connect_openrouter_hint"))
        self.oauth_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.oauth_btn.setStyleSheet("""
            QPushButton {
                background-color: #2e7d32;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover { background-color: #388e3c; }
            QPushButton:disabled { background-color: #3a3a5a; color: #888888; }
        """)
        self.oauth_btn.clicked.connect(self._start_oauth)
        api_layout.addWidget(self.oauth_btn)

        self.oauth_status = QLabel("")
        self.oauth_status.setStyleSheet("color: #8899aa; font-size: 11px;")
        self.oauth_status.setWordWrap(True)
        self.oauth_status.hide()
        api_layout.addWidget(self.oauth_status)

        self._oauth_worker = None

        layout.addWidget(api_group)

        # === Модели ===
        models_group = QGroupBox(t("models"))
        models_layout = QVBoxLayout(models_group)

        # Ссылка на OpenRouter + кнопка добавить
        header_layout = QHBoxLayout()

        # Каталог
        link_catalog = QLabel(
            f'<a href="https://openrouter.ai/models?fmt=cards&input_modalities=text%2Cimage&modality=text%2Bimage-%3Etext" style="color: #4fc3f7; text-decoration: none;">{t("models_catalog")}</a>'
        )
        link_catalog.setOpenExternalLinks(True)
        header_layout.addWidget(link_catalog)

        header_layout.addSpacing(10)

        # Бесплатные
        link_free = QLabel(
            f'<a href="https://openrouter.ai/models?fmt=cards&input_modalities=text%2Cimage&max_price=0&output_modalities=text&order=top-weekly" style="color: #81c784; text-decoration: none;">{t("models_free")}</a>'
        )
        link_free.setOpenExternalLinks(True)
        header_layout.addWidget(link_free)

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

        # === Телеметрия ===
        self.telemetry_checkbox = QCheckBox(t("telemetry_optin"))
        self.telemetry_checkbox.setToolTip(t("telemetry_tooltip"))
        layout.addWidget(self.telemetry_checkbox)

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
            self.api_key_input.setPlaceholderText("sk-...")

        # Ключи храним по-провайдерно: запоминаем текущий, показываем нужный
        if self._active_key_provider and self._active_key_provider != provider:
            self._provider_keys[self._active_key_provider] = (
                self.api_key_input.text().strip()
            )
        self.api_key_input.setText(self._provider_keys.get(provider, ""))
        self._active_key_provider = provider

        # OAuth-кнопка — только для OpenRouter
        if hasattr(self, "oauth_btn"):
            self.oauth_btn.setVisible(provider == "openrouter")
            if provider != "openrouter":
                self.oauth_status.hide()

    # === OAuth подключение OpenRouter ===

    def _start_oauth(self):
        """Запустить OAuth-флоу в фоне"""
        if self._oauth_worker and self._oauth_worker.isRunning():
            return

        self.oauth_btn.setEnabled(False)
        self.oauth_status.setText(t("oauth_waiting"))
        self.oauth_status.show()

        self._oauth_worker = OAuthWorker()
        self._oauth_worker.success.connect(self._on_oauth_success)
        self._oauth_worker.failed.connect(self._on_oauth_failed)
        self._oauth_worker.start()

        # Прячем настройки и оверлей (они topmost и закрывают браузер);
        # вернём их, когда флоу завершится
        self._hidden_for_oauth = True
        overlay = self.parent()
        if overlay is not None and overlay.isVisible():
            self._overlay_was_visible = True
            overlay.hide()
        else:
            self._overlay_was_visible = False
        self.hide()

    def _restore_after_oauth(self):
        """Вернуть окна после завершения OAuth"""
        if not getattr(self, "_hidden_for_oauth", False):
            return
        self._hidden_for_oauth = False
        overlay = self.parent()
        if overlay is not None and self._overlay_was_visible:
            overlay.show()
        self.show()
        self.raise_()
        self.activateWindow()

    def _on_oauth_success(self, api_key: str, models: list):
        """Ключ получен — заполняем поле и добавляем бесплатные модели"""
        self._restore_after_oauth()
        self.api_key_input.setText(api_key)

        # Добавляем модели, которых ещё нет в списке
        existing = set()
        for i in range(self.models_layout_inner.count()):
            widget = self.models_layout_inner.itemAt(i).widget()
            if widget and isinstance(widget, QFrame):
                existing.add(widget.property("model_id"))

        for model_id, display_name in models:
            if model_id not in existing:
                self._add_model_item(model_id, display_name)

        self.oauth_btn.setEnabled(True)
        self.oauth_status.setText(t("oauth_success"))
        self.oauth_status.setStyleSheet("color: #81c784; font-size: 11px;")

    def _on_oauth_failed(self, error: str):
        """OAuth не удался"""
        self._restore_after_oauth()
        self.oauth_btn.setEnabled(True)
        self.oauth_status.setText(f"{t('oauth_error')} {error[:120]}")
        self.oauth_status.setStyleSheet("color: #ff6b6b; font-size: 11px;")

    def done(self, result):
        """Закрытие диалога — останавливаем OAuth, если ждёт"""
        if self._oauth_worker and self._oauth_worker.isRunning():
            self._oauth_worker.stop()
            self._oauth_worker.wait(3000)
        super().done(result)

    def _load_current_settings(self):
        """Загрузить текущие настройки в поля"""
        # API провайдер
        provider = self.current_settings.get("api_provider", "openrouter")
        index = self.provider_combo.findData(provider)
        if index >= 0:
            self.provider_combo.setCurrentIndex(index)

        # API ключ подставляется в _on_provider_changed из _provider_keys

        # Модели
        models = self.current_settings.get("models", [])
        for model_id, display_name in models:
            self._add_model_item(model_id, display_name)

        # Горячие клавиши
        hotkey_overlay = self.current_settings.get("hotkey_overlay", "PageUp")
        hotkey_screenshot = self.current_settings.get("hotkey_screenshot", "PageDown")

        self.hotkey_overlay.setKeySequence(QKeySequence(hotkey_overlay))
        self.hotkey_screenshot.setKeySequence(QKeySequence(hotkey_screenshot))

        # Автозапуск
        autostart = self.current_settings.get("autostart", False)
        self.autostart_checkbox.setChecked(autostart)

        # Телеметрия (по умолчанию включена)
        telemetry_enabled = self.current_settings.get("telemetry_enabled", True)
        self.telemetry_checkbox.setChecked(bool(telemetry_enabled))

        # Видимость OAuth-кнопки под текущего провайдера
        self._on_provider_changed(self.provider_combo.currentIndex())

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
        model_id, ok = QInputDialog.getText(self, t("add_model"), t("model_id_prompt"))
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
                    "OpenRouter API key should start with 'sk-or-'",
                )
                return
            elif api_provider == "routerai" and not api_key.startswith("sk-"):
                QMessageBox.warning(
                    self,
                    t("error").replace("❌ ", ""),
                    "RouterAI API key should start with 'sk-'",
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
            hotkey_overlay = "PageUp"
        if not hotkey_screenshot:
            hotkey_screenshot = "PageDown"

        # Автозапуск
        autostart = self.autostart_checkbox.isChecked()

        # Телеметрия
        telemetry_enabled = self.telemetry_checkbox.isChecked()

        # Ключи по-провайдерно (текущее поле — ключ выбранного провайдера)
        self._provider_keys[api_provider] = api_key

        # Формируем настройки (api_key — легаси-поле для обратной совместимости)
        new_settings = {
            **self.current_settings,
            "api_provider": api_provider,
            "api_key": api_key,
            "api_keys": dict(self._provider_keys),
            "models": models,
            "hotkey_overlay": hotkey_overlay,
            "hotkey_screenshot": hotkey_screenshot,
            "autostart": autostart,
            "telemetry_enabled": telemetry_enabled,
        }

        # Отправляем сигнал
        self.settings_saved.emit(new_settings)
        self.accept()

    def get_settings(self):
        """Получить текущие настройки из полей"""
        return {
            "api_key": self.api_key_input.text().strip(),
            "hotkey_overlay": self.hotkey_overlay.keySequence().toString() or "PageUp",
            "hotkey_screenshot": self.hotkey_screenshot.keySequence().toString()
            or "PageDown",
        }
