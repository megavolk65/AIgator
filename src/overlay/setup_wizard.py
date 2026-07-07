"""
Мастер первого запуска — три пути подключения AI:
  1. Бесплатно (OpenRouter OAuth + free-модели)
  2. Рублями (RouterAI, пошагово с проверкой ключа) — только в русском UI
  3. OpenRouter платно (OAuth + пополнение)
"""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QCheckBox,
    QStackedWidget,
    QWidget,
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QUrl
from PyQt6.QtGui import QDesktopServices

import requests

from src.localization import Localization, t
from .settings_dialog import OAuthWorker

# Рекомендуемые платные модели для RouterAI (недорогие, обе с vision)
ROUTERAI_STARTER_MODELS = [
    ("google/gemini-3.1-flash-lite-preview", "GOOGLE: Gemini 3.1 Flash Lite"),
    ("openai/gpt-5-mini", "OPENAI: GPT-5 Mini"),
]

WIZARD_STYLE = """
    QDialog { background-color: #1a1a2e; color: #ffffff; }
    QLabel { color: #cccccc; }
    QLabel#pageTitle { color: #ffffff; font-size: 20px; font-weight: bold; }
    QLabel#choiceDesc { color: #8899aa; font-size: 12px; }
    QPushButton {
        background-color: #3a3a5a; border: none; border-radius: 8px;
        padding: 10px 15px; color: #ffffff;
    }
    QPushButton:hover { background-color: #4a4a6a; }
    QPushButton:disabled { background-color: #2a2a3a; color: #777777; }
    QPushButton#choiceBtn {
        font-size: 16px; font-weight: bold; text-align: left; padding: 14px 18px;
    }
    QPushButton#oauthBtn {
        background-color: #2e7d32; font-weight: bold; font-size: 14px; padding: 12px;
    }
    QPushButton#oauthBtn:hover { background-color: #388e3c; }
    QPushButton#finishBtn {
        background-color: #1565c0; font-weight: bold; font-size: 14px; padding: 12px;
    }
    QPushButton#finishBtn:hover { background-color: #1976d2; }
    QPushButton#linkBtn {
        background: transparent; color: #8899aa; text-decoration: underline;
        padding: 4px;
    }
    QPushButton#linkBtn:hover { color: #4fc3f7; }
    QLineEdit {
        background-color: #2a2a4a; border: 1px solid #3a3a5a; border-radius: 5px;
        padding: 8px; color: #ffffff;
    }
    QLineEdit:focus { border-color: #667eea; }
    QCheckBox { color: #cccccc; }
"""


class RouterAIKeyWorker(QThread):
    """Проверка ключа RouterAI тестовым запросом баланса"""

    result = pyqtSignal(bool, str)  # ok, balance_or_error

    def __init__(self, api_key: str):
        super().__init__()
        self.api_key = api_key

    def run(self):
        try:
            r = requests.get(
                "https://routerai.ru/api/v1/credits",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=20,
            )
            r.raise_for_status()
            credits = r.json().get("data", {}).get("credits", 0)
            self.result.emit(True, f"{credits:.2f}")
        except Exception as e:
            self.result.emit(False, str(e)[:120])


class SetupWizard(QDialog):
    """Мастер первого запуска"""

    completed = pyqtSignal(dict)      # готовые настройки для сохранения
    open_settings = pyqtSignal()      # «я разберусь сам»

    PAGE_CHOICE, PAGE_OAUTH, PAGE_ROUTERAI = 0, 1, 2

    def __init__(self, parent=None, current_settings=None):
        super().__init__(parent)
        self.settings = dict(current_settings or {})

        self._oauth_worker = None
        self._key_worker = None
        self._oauth_key = ""          # ключ, полученный через OAuth
        self._oauth_models = []       # модели, подобранные после OAuth
        self._oauth_paid_mode = False # страница OAuth в «платном» режиме
        self._hidden_for_oauth = False
        self._overlay_was_visible = False

        self.setWindowTitle(t("wizard_title"))
        self.setFixedSize(560, 480)
        self.setStyleSheet(WIZARD_STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(25, 20, 25, 20)
        self.stack = QStackedWidget()
        root.addWidget(self.stack)

        self.stack.addWidget(self._build_choice_page())    # 0
        self.stack.addWidget(self._build_oauth_page())     # 1
        self.stack.addWidget(self._build_routerai_page())  # 2

    # ================= Страница выбора =================

    def _build_choice_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(12)

        title = QLabel(t("wizard_welcome"))
        title.setObjectName("pageTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)
        lay.addSpacing(8)

        def add_choice(btn_text, desc_text, handler):
            btn = QPushButton(btn_text)
            btn.setObjectName("choiceBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(handler)
            lay.addWidget(btn)
            desc = QLabel(desc_text)
            desc.setObjectName("choiceDesc")
            desc.setWordWrap(True)
            desc.setContentsMargins(18, 0, 0, 6)
            lay.addWidget(desc)

        add_choice(t("wizard_free_btn"), t("wizard_free_desc"), self._go_free)

        # Рублёвая ветка — только в русском интерфейсе
        if Localization.get_language() == "ru":
            add_choice(t("wizard_rub_btn"), t("wizard_rub_desc"), self._go_routerai)

        add_choice(t("wizard_paid_btn"), t("wizard_paid_desc"), self._go_paid)

        lay.addStretch()

        self_link = QPushButton(t("wizard_self_link"))
        self_link.setObjectName("linkBtn")
        self_link.setCursor(Qt.CursorShape.PointingHandCursor)
        self_link.clicked.connect(self._on_self_link)
        lay.addWidget(self_link, alignment=Qt.AlignmentFlag.AlignCenter)

        return page

    # ================= Страница OAuth (бесплатно / платно) =================

    def _build_oauth_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(12)

        self.oauth_title = QLabel("")
        self.oauth_title.setObjectName("pageTitle")
        lay.addWidget(self.oauth_title)

        note = QLabel(t("wizard_oauth_note"))
        note.setWordWrap(True)
        lay.addWidget(note)

        self.oauth_go_btn = QPushButton(t("connect_openrouter"))
        self.oauth_go_btn.setObjectName("oauthBtn")
        self.oauth_go_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.oauth_go_btn.clicked.connect(self._start_oauth)
        lay.addWidget(self.oauth_go_btn)

        self.oauth_status = QLabel("")
        self.oauth_status.setWordWrap(True)
        lay.addWidget(self.oauth_status)

        # Блок пополнения (только в платном режиме)
        self.topup_label = QLabel(t("wizard_or_topup"))
        self.topup_label.setWordWrap(True)
        lay.addWidget(self.topup_label)

        self.topup_btn = QPushButton("💳 openrouter.ai/credits")
        self.topup_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.topup_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://openrouter.ai/credits"))
        )
        lay.addWidget(self.topup_btn)

        # Веб-поиск (только в платном режиме)
        self.oauth_websearch = QCheckBox(t("wizard_websearch_q"))
        lay.addWidget(self.oauth_websearch)

        lay.addStretch()
        lay.addLayout(self._nav_row("oauth"))
        return page

    # ================= Страница RouterAI =================

    def _build_routerai_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(10)

        title = QLabel(t("wizard_ra_title"))
        title.setObjectName("pageTitle")
        lay.addWidget(title)

        step1_row = QHBoxLayout()
        step1_row.addWidget(QLabel(t("wizard_ra_step1")))
        site_btn = QPushButton("🌐 routerai.ru")
        site_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        site_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://routerai.ru"))
        )
        step1_row.addWidget(site_btn)
        step1_row.addStretch()
        lay.addLayout(step1_row)

        lay.addWidget(QLabel(t("wizard_ra_step2")))
        lay.addWidget(QLabel(t("wizard_ra_step3")))

        key_row = QHBoxLayout()
        self.ra_key_input = QLineEdit()
        self.ra_key_input.setPlaceholderText("sk-...")
        self.ra_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        key_row.addWidget(self.ra_key_input, 1)

        self.ra_check_btn = QPushButton(t("wizard_check_key"))
        self.ra_check_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ra_check_btn.clicked.connect(self._check_routerai_key)
        key_row.addWidget(self.ra_check_btn)
        lay.addLayout(key_row)

        self.ra_status = QLabel("")
        self.ra_status.setWordWrap(True)
        lay.addWidget(self.ra_status)

        self.ra_websearch = QCheckBox(t("wizard_websearch_q"))
        lay.addWidget(self.ra_websearch)

        lay.addStretch()
        lay.addLayout(self._nav_row("ra"))
        return page

    # ================= Навигация =================

    def _nav_row(self, prefix: str):
        row = QHBoxLayout()
        back = QPushButton(t("wizard_back"))
        back.setCursor(Qt.CursorShape.PointingHandCursor)
        back.clicked.connect(lambda: self.stack.setCurrentIndex(self.PAGE_CHOICE))
        row.addWidget(back)
        row.addStretch()

        finish = QPushButton(t("wizard_finish"))
        finish.setObjectName("finishBtn")
        finish.setCursor(Qt.CursorShape.PointingHandCursor)
        finish.setEnabled(False)
        if prefix == "oauth":
            finish.clicked.connect(self._finish_oauth)
            self.oauth_finish_btn = finish
        else:
            finish.clicked.connect(self._finish_routerai)
            self.ra_finish_btn = finish
        row.addWidget(finish)
        return row

    def _go_free(self):
        self._oauth_paid_mode = False
        self.oauth_title.setText(t("wizard_free_title"))
        self.topup_label.hide()
        self.topup_btn.hide()
        self.oauth_websearch.hide()
        self.oauth_websearch.setChecked(False)
        self.stack.setCurrentIndex(self.PAGE_OAUTH)

    def _go_paid(self):
        self._oauth_paid_mode = True
        self.oauth_title.setText(t("wizard_paid_title"))
        self.topup_label.show()
        self.topup_btn.show()
        self.oauth_websearch.show()
        self.stack.setCurrentIndex(self.PAGE_OAUTH)

    def _go_routerai(self):
        self.stack.setCurrentIndex(self.PAGE_ROUTERAI)

    def _on_self_link(self):
        self.open_settings.emit()
        self.close()

    # ================= OAuth =================

    def _start_oauth(self):
        if self._oauth_worker and self._oauth_worker.isRunning():
            return
        self.oauth_go_btn.setEnabled(False)
        self.oauth_status.setText(t("oauth_waiting"))

        self._oauth_worker = OAuthWorker()
        self._oauth_worker.success.connect(self._on_oauth_success)
        self._oauth_worker.failed.connect(self._on_oauth_failed)
        self._oauth_worker.start()

        # Прячем окна — они topmost и закрывают браузер
        self._hidden_for_oauth = True
        overlay = self.parent()
        self._overlay_was_visible = overlay is not None and overlay.isVisible()
        if self._overlay_was_visible:
            overlay.hide()
        self.hide()

    def _restore_after_oauth(self):
        if not self._hidden_for_oauth:
            return
        self._hidden_for_oauth = False
        overlay = self.parent()
        if overlay is not None and self._overlay_was_visible:
            overlay.show()
        self.show()
        self.raise_()
        self.activateWindow()

    def _on_oauth_success(self, api_key: str, models: list):
        self._restore_after_oauth()
        self._oauth_key = api_key
        self._oauth_models = models

        names = ", ".join(name for _, name in models)
        self.oauth_status.setText(f"✅ {names}")
        self.oauth_status.setStyleSheet("color: #81c784;")
        self.oauth_go_btn.setEnabled(True)
        self.oauth_finish_btn.setEnabled(True)

    def _on_oauth_failed(self, error: str):
        self._restore_after_oauth()
        self.oauth_go_btn.setEnabled(True)
        self.oauth_status.setText(f"{t('oauth_error')} {error[:120]}")
        self.oauth_status.setStyleSheet("color: #ff6b6b;")

    def _finish_oauth(self):
        self._emit_completed(
            provider="openrouter",
            api_key=self._oauth_key,
            new_models=self._oauth_models,
            web_search=self.oauth_websearch.isChecked(),
        )

    # ================= RouterAI =================

    def _check_routerai_key(self):
        key = self.ra_key_input.text().strip()
        if not key:
            return
        self.ra_check_btn.setEnabled(False)
        self.ra_status.setText(t("wizard_key_checking"))
        self.ra_status.setStyleSheet("color: #8899aa;")

        self._key_worker = RouterAIKeyWorker(key)
        self._key_worker.result.connect(self._on_key_checked)
        self._key_worker.start()

    def _on_key_checked(self, ok: bool, message: str):
        self.ra_check_btn.setEnabled(True)
        if ok:
            names = ", ".join(name for _, name in ROUTERAI_STARTER_MODELS)
            self.ra_status.setText(
                t("wizard_key_ok").format(balance=message, models=names)
            )
            self.ra_status.setStyleSheet("color: #81c784;")
            self.ra_finish_btn.setEnabled(True)
        else:
            self.ra_status.setText(t("wizard_key_fail").format(error=message))
            self.ra_status.setStyleSheet("color: #ff6b6b;")

    def _finish_routerai(self):
        self._emit_completed(
            provider="routerai",
            api_key=self.ra_key_input.text().strip(),
            new_models=list(ROUTERAI_STARTER_MODELS),
            web_search=self.ra_websearch.isChecked(),
        )

    # ================= Завершение =================

    def _emit_completed(self, provider, api_key, new_models, web_search):
        upd = dict(self.settings)

        upd["api_provider"] = provider
        keys = dict(upd.get("api_keys") or {})
        keys[provider] = api_key
        upd["api_keys"] = keys
        upd["api_key"] = api_key  # легаси-поле

        # Добавляем модели без дублей
        models = [list(m) for m in (upd.get("models") or [])]
        existing_ids = {m[0] for m in models}
        for model_id, display_name in new_models:
            if model_id not in existing_ids:
                models.append([model_id, display_name])
        upd["models"] = models

        if new_models:
            upd["selected_model"] = new_models[0][0]

        upd["web_search"] = bool(web_search)
        upd["setup_completed"] = True

        self.completed.emit(upd)
        self.close()

    def closeEvent(self, event):
        """Останавливаем фоновые потоки при закрытии"""
        if self._oauth_worker and self._oauth_worker.isRunning():
            self._oauth_worker.stop()
            self._oauth_worker.wait(3000)
        if self._key_worker and self._key_worker.isRunning():
            self._key_worker.wait(2000)
        super().closeEvent(event)
