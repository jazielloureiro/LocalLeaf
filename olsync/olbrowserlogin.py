"""Ol Browser Login Utility"""

##################################################
# MIT License
##################################################
# File: olbrowserlogin.py
# Description: Overleaf Browser Login Utility
# Author: Moritz Glöckl
# License: MIT
# Version: 1.2.0
##################################################

from PySide6.QtCore import QCoreApplication, QLoggingCategory, QUrl
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineSettings,
)

from settings import Settings


class OlBrowserLogin:
    """
    Overleaf Browser Login Utility
    Opens a browser window to securely login the user and returns relevant login data.
    """

    def __init__(self):
        self._cookies = {}
        self._csrf = ""
        self._login_success = False
        self._settings = Settings()

    def _create_main_window(self):
        web_engine_context_log = QLoggingCategory("qt.webenginecontext")
        web_engine_context_log.setFilterRules("*.info=false")
        web_engine_context_log.setFilterRules("*.warning=false")

        self._window = QMainWindow()

        self._window.webview = QWebEngineView()

        self._window.profile = QWebEngineProfile(self._window.webview)
        self._window.cookie_store = self._window.profile.cookieStore()
        self._window.cookie_store.cookieAdded.connect(self._handle_cookie_added)
        self._window.profile.setPersistentCookiesPolicy(
            QWebEngineProfile.NoPersistentCookies
        )

        self._window.profile.settings().setAttribute(
            QWebEngineSettings.JavascriptEnabled, True
        )

        webpage = QWebEnginePage(self._window.profile, self._window)
        self._window.webview.setPage(webpage)
        self._window.webview.load(QUrl.fromUserInput(self._settings.login_url()))
        self._window.webview.loadFinished.connect(self._handle_login_load_finished)

        self._window.setCentralWidget(self._window.webview)
        self._window.resize(600, 700)
        self._window.show()

    def _handle_login_load_finished(self):
        def callback(result):
            self._window.webview.load(QUrl.fromUserInput(result))
            self._window.webview.loadFinished.connect(
                self._handle_project_load_finished
            )

        if self._window.webview.url().toString() == self._settings.project_url():
            self._window.webview.page().runJavaScript(
                "document.getElementsByClassName('dash-cell-name')[1].firstChild.href",
                0,
                callback,
            )

    def _handle_project_load_finished(self):
        def callback(result):
            self._csrf = result
            self._login_success = True
            QCoreApplication.quit()

        self._window.webview.page().runJavaScript(
            "document.getElementsByName('ol-csrfToken')[0].content", 0, callback
        )

    def _handle_cookie_added(self, cookie):
        cookie_name = cookie.name().data().decode("utf-8")
        if cookie_name in ["overleaf_session2", "GCLB"]:
            self._cookies[cookie_name] = cookie.value().data().decode("utf-8")

    def login(self):
        app = QApplication([])
        self._create_main_window()
        app.exec()

        if not self._login_success:
            return None

        return {"cookie": self._cookies, "csrf": self._csrf}
