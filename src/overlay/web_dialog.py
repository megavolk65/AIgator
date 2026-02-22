"""
Диалог встроенного браузера для просмотра ссылок
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QProgressBar
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage

from src.localization import t


class WebDialog(QDialog):
    """Встроенный браузер"""
    
    def __init__(self, parent=None, url: str = ""):
        super().__init__(parent)
        self._init_ui()
        if url:
            self.load_url(url)
    
    def _init_ui(self):
        """Инициализация интерфейса"""
        self.setWindowTitle(t("view"))
        self.resize(1350, 1050)
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint |
            Qt.WindowType.WindowMinimizeButtonHint
        )
        # Немодальный режим - не блокирует главное окно
        self.setModal(False)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # === Панель навигации ===
        nav_bar = QHBoxLayout()
        nav_bar.setContentsMargins(8, 8, 8, 8)
        nav_bar.setSpacing(8)
        
        # Кнопка назад
        self.back_btn = QPushButton()
        self.back_btn.setText("<")
        self.back_btn.setFixedSize(32, 32)
        self.back_btn.clicked.connect(self._go_back)
        self.back_btn.setStyleSheet(self._button_style())
        nav_bar.addWidget(self.back_btn)
        
        # Кнопка вперёд
        self.forward_btn = QPushButton()
        self.forward_btn.setText(">")
        self.forward_btn.setFixedSize(32, 32)
        self.forward_btn.clicked.connect(self._go_forward)
        self.forward_btn.setStyleSheet(self._button_style())
        nav_bar.addWidget(self.forward_btn)
        
        # Кнопка обновить
        self.reload_btn = QPushButton()
        self.reload_btn.setText("↻")
        self.reload_btn.setFixedSize(32, 32)
        self.reload_btn.clicked.connect(self._reload)
        self.reload_btn.setStyleSheet(self._button_style())
        nav_bar.addWidget(self.reload_btn)
        
        # URL label
        self.url_label = QLabel()
        self.url_label.setStyleSheet("""
            QLabel {
                color: #aaaaaa;
                background-color: #2a2a4a;
                border-radius: 4px;
                padding: 6px 10px;
            }
        """)
        nav_bar.addWidget(self.url_label, 1)
        
        # Кнопка открыть в браузере
        self.external_btn = QPushButton()
        self.external_btn.setText(t("open_in_browser"))
        self.external_btn.clicked.connect(self._open_external)
        self.external_btn.setStyleSheet(self._button_style())
        nav_bar.addWidget(self.external_btn)
        
        # Кнопка закрыть
        self.close_btn = QPushButton()
        self.close_btn.setText("X")
        self.close_btn.setFixedSize(32, 32)
        self.close_btn.clicked.connect(self.close)
        self.close_btn.setStyleSheet("""
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
            }
        """)
        nav_bar.addWidget(self.close_btn)
        
        layout.addLayout(nav_bar)
        
        # === Прогресс бар ===
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(3)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1a1a2e;
                border: none;
            }
            QProgressBar::chunk {
                background-color: #667eea;
            }
        """)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        
        # === Web View ===
        self.web_view = QWebEngineView()
        self.web_view.loadStarted.connect(self._on_load_started)
        self.web_view.loadProgress.connect(self._on_load_progress)
        self.web_view.loadFinished.connect(self._on_load_finished)
        self.web_view.urlChanged.connect(self._on_url_changed)
        self.web_view.titleChanged.connect(self._on_title_changed)
        layout.addWidget(self.web_view)
        
        # Стили диалога
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a2e;
            }
        """)
    
    def _button_style(self) -> str:
        return """
            QPushButton {
                background-color: #3a3a5a;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #4a4a6a;
            }
            QPushButton:disabled {
                background-color: #2a2a4a;
                color: #666666;
            }
        """
    
    def load_url(self, url: str):
        """Загрузить URL"""
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        self.web_view.setUrl(QUrl(url))
    
    def _go_back(self):
        self.web_view.back()
    
    def _go_forward(self):
        self.web_view.forward()
    
    def _reload(self):
        self.web_view.reload()
    
    def _open_external(self):
        """Открыть во внешнем браузере"""
        from PyQt6.QtGui import QDesktopServices
        QDesktopServices.openUrl(self.web_view.url())
    
    def _on_load_started(self):
        self.progress_bar.setValue(0)
        self.progress_bar.show()
    
    def _on_load_progress(self, progress: int):
        self.progress_bar.setValue(progress)
    
    def _on_load_finished(self, ok: bool):
        self.progress_bar.hide()
        self._update_nav_buttons()
    
    def _on_url_changed(self, url: QUrl):
        display_url = url.toString()
        if len(display_url) > 60:
            display_url = display_url[:57] + "..."
        self.url_label.setText(display_url)
    
    def _on_title_changed(self, title: str):
        if title:
            self.setWindowTitle(f"{title} - {t('view')}")
        else:
            self.setWindowTitle(t("view"))
    
    def _update_nav_buttons(self):
        self.back_btn.setEnabled(self.web_view.history().canGoBack())
        self.forward_btn.setEnabled(self.web_view.history().canGoForward())
