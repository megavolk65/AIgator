"""
Диалог встроенного браузера для просмотра ссылок
"""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLineEdit,
    QProgressBar,
    QTabWidget,
    QWidget,
    QTabBar,
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage

from src.localization import t


class CustomWebEnginePage(QWebEnginePage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.add_tab_callback = None
        self.is_new_window = False

    def acceptNavigationRequest(self, url, _type, isMainFrame):
        if (
            _type == QWebEnginePage.NavigationType.NavigationTypeLinkClicked
            and self.add_tab_callback
            and isMainFrame
        ):
            if self.is_new_window:
                # First navigation in a new window (e.g. from context menu "Open in new tab")
                self.is_new_window = False
                return super().acceptNavigationRequest(url, _type, isMainFrame)

            # Любой клик по ссылке открываем в новой вкладке
            self.add_tab_callback(url.toString())
            return False

        self.is_new_window = False
        return super().acceptNavigationRequest(url, _type, isMainFrame)

    def createWindow(self, _type):
        if self.add_tab_callback:
            # Срабатывает при "Открыть в новой вкладке" из контекстного меню или target="_blank"
            new_view = self.add_tab_callback("")
            new_page = new_view.page()
            if isinstance(new_page, CustomWebEnginePage):
                new_page.is_new_window = True
            return new_page
        return super().createWindow(_type)


class WebDialog(QDialog):
    """Встроенный браузер с вкладками"""

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
            Qt.WindowType.Window
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowMinimizeButtonHint
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

        # URL input
        self.url_input = QLineEdit()
        self.url_input.setStyleSheet("""
            QLineEdit {
                color: #ffffff;
                background-color: #2a2a4a;
                border: 1px solid #3a3a5a;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #667eea;
            }
        """)
        self.url_input.returnPressed.connect(self._on_url_input_entered)
        nav_bar.addWidget(self.url_input, 1)

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

        # === Tabs ===
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self._close_tab)
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

        # Добавляем вкладку "+"
        self.plus_tab_widget = QWidget()
        self.tab_widget.addTab(self.plus_tab_widget, "+")
        self.tab_widget.tabBar().setTabButton(0, QTabBar.ButtonPosition.RightSide, None)
        self.tab_widget.tabBar().setTabButton(0, QTabBar.ButtonPosition.LeftSide, None)

        layout.addWidget(self.tab_widget)

        # Стили диалога
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a2e;
            }
            QTabWidget::pane {
                border: none;
                background-color: #1a1a2e;
            }
            QTabBar::tab {
                background-color: #2a2a4a;
                color: #aaaaaa;
                padding: 6px 12px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #3a3a5a;
                color: #ffffff;
            }
            QTabBar::tab:hover:!selected {
                background-color: #353555;
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
        """Загрузить URL (используется для начальной загрузки или внешних вызовов)"""
        if self.tab_widget.count() <= 1:
            self.add_tab(url)
        else:
            # Если вкладки уже есть, открываем в текущей
            web_view = self._get_current_web_view()
            if web_view:
                if not url.startswith(("http://", "https://")):
                    url = "https://" + url
                web_view.setUrl(QUrl(url))

    def add_tab(self, url: str = "") -> QWebEngineView:
        """Добавить новую вкладку"""
        web_view = QWebEngineView()

        # Настраиваем кастомную страницу для открытия ссылок в новых вкладках
        page = CustomWebEnginePage(web_view)
        page.add_tab_callback = self.add_tab
        web_view.setPage(page)

        # Скрываем пункт "Открыть в новом окне" из стандартного меню
        action_new_window = page.action(QWebEnginePage.WebAction.OpenLinkInNewWindow)
        if action_new_window:
            action_new_window.setVisible(False)

        web_view.loadStarted.connect(self._on_load_started)
        web_view.loadProgress.connect(self._on_load_progress)
        web_view.loadFinished.connect(self._on_load_finished)
        web_view.urlChanged.connect(self._on_url_changed)
        web_view.titleChanged.connect(self._on_title_changed)

        title = t("loading") if url else t("view")

        # Находим индекс вкладки "+"
        plus_index = -1
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == "+":
                plus_index = i
                break

        if plus_index != -1:
            index = self.tab_widget.insertTab(plus_index, web_view, title)
        else:
            index = self.tab_widget.addTab(web_view, title)

        self.tab_widget.setCurrentIndex(index)

        # Убеждаемся, что у вкладки "+" нет кнопки закрытия после вставки новой вкладки
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == "+":
                self.tab_widget.tabBar().setTabButton(
                    i, QTabBar.ButtonPosition.RightSide, None
                )
                self.tab_widget.tabBar().setTabButton(
                    i, QTabBar.ButtonPosition.LeftSide, None
                )

        if url:
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            web_view.setUrl(QUrl(url))

        return web_view

    def _close_tab(self, index: int):
        if self.tab_widget.tabText(index) == "+":
            return

        widget = self.tab_widget.widget(index)
        if widget:
            widget.deleteLater()
        self.tab_widget.removeTab(index)

        if self.tab_widget.count() <= 1:
            self.close()

    def _on_tab_changed(self, index: int):
        if index >= 0 and self.tab_widget.tabText(index) == "+":
            # Кликнули на вкладку "+", добавляем новую вкладку
            self.add_tab()
            return

        self._update_nav_buttons()
        web_view = self._get_current_web_view()
        if web_view:
            # Force update of URL
            url_str = web_view.url().toString()
            self.url_input.setText(url_str)
            self.url_input.clearFocus()

            # Force update of Title
            title = web_view.title()
            if title:
                self.setWindowTitle(f"{title} - {t('view')}")
            else:
                self.setWindowTitle(t("view"))

    def _get_current_web_view(self) -> QWebEngineView:
        widget = self.tab_widget.currentWidget()
        if isinstance(widget, QWebEngineView):
            return widget
        return None

    def _go_back(self):
        web_view = self._get_current_web_view()
        if web_view:
            web_view.back()

    def _go_forward(self):
        web_view = self._get_current_web_view()
        if web_view:
            web_view.forward()

    def _reload(self):
        web_view = self._get_current_web_view()
        if web_view:
            web_view.reload()

    def _open_external(self):
        """Открыть во внешнем браузере"""
        from PyQt6.QtGui import QDesktopServices

        web_view = self._get_current_web_view()
        if web_view:
            QDesktopServices.openUrl(web_view.url())

    def _on_load_started(self):
        web_view = self.sender()
        if web_view == self._get_current_web_view():
            self.progress_bar.setValue(0)
            self.progress_bar.show()

    def _on_load_progress(self, progress: int):
        web_view = self.sender()
        if web_view == self._get_current_web_view():
            self.progress_bar.setValue(progress)

    def _on_load_finished(self, ok: bool):
        web_view = self.sender()
        if web_view == self._get_current_web_view():
            self.progress_bar.hide()
            self._update_nav_buttons()

    def _on_url_changed(self, url: QUrl):
        if isinstance(url, str):
            display_url = url
        else:
            display_url = url.toString()

        web_view = self.sender()
        # sender() can be None if called directly from _on_tab_changed
        if not web_view or web_view == self._get_current_web_view():
            self.url_input.setText(display_url)
            # Clear focus so the text isn't selected initially and cursor isn't active
            self.url_input.clearFocus()

    def _on_url_input_entered(self):
        """Обработка ввода URL в адресную строку"""
        url = self.url_input.text().strip()
        if not url:
            return

        web_view = self._get_current_web_view()
        if web_view:
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            web_view.setUrl(QUrl(url))

    def _on_title_changed(self, title: str):
        web_view = self.sender()
        if web_view:
            index = self.tab_widget.indexOf(web_view)
            if index != -1:
                display_title = title[:20] + "..." if len(title) > 20 else title
                if not display_title:
                    display_title = t("view")
                self.tab_widget.setTabText(index, display_title)

        # Update main window title if it's the current tab
        if not web_view or web_view == self._get_current_web_view():
            if title:
                self.setWindowTitle(f"{title} - {t('view')}")
            else:
                self.setWindowTitle(t("view"))

    def _update_nav_buttons(self):
        web_view = self._get_current_web_view()
        if web_view:
            self.back_btn.setEnabled(web_view.history().canGoBack())
            self.forward_btn.setEnabled(web_view.history().canGoForward())
        else:
            self.back_btn.setEnabled(False)
            self.forward_btn.setEnabled(False)
