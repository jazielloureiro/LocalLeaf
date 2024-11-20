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
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings

# Where to get the CSRF Token and where to send the login request to
LOGIN_URL = "https://www.overleaf.com/login"
PROJECT_URL = "https://www.overleaf.com/project"  # The dashboard URL
# JS snippet to extract the path of the first project from the project list
JAVASCRIPT_PROJECT_PATH_EXTRACTOR = "document.getElementsByClassName('dash-cell-name')[1].firstChild.href"
# JS snippet to extract the csrfToken
JAVASCRIPT_CSRF_EXTRACTOR = "document.getElementsByName('ol-csrfToken')[0].content"
# Name of the cookies we want to extract
COOKIE_NAMES = ["overleaf_session2", "GCLB"]


class OlBrowserLogin(QMainWindow):
    """
    Overleaf Browser Login Utility
    Opens a browser window to securely login the user and returns relevant login data.
    """

    def __init__(self):
        self._cookies = {}
        self._csrf = ""
        self._login_success = False
    
    def _create_main_window(self):
        self._window = QMainWindow()

        self._window.webview = QWebEngineView()

        self._window.profile = QWebEngineProfile(self._window.webview)
        self._window.cookie_store = self._window.profile.cookieStore()
        self._window.cookie_store.cookieAdded.connect(self._handle_cookie_added)
        self._window.profile.setPersistentCookiesPolicy(QWebEngineProfile.NoPersistentCookies)

        self._window.profile.settings().setAttribute(QWebEngineSettings.JavascriptEnabled, True)

        webpage = QWebEnginePage(self._window.profile, self._window)
        self._window.webview.setPage(webpage)
        self._window.webview.load(QUrl.fromUserInput(LOGIN_URL))
        self._window.webview.loadFinished.connect(self._handle_login_load_finished)

        self._window.setCentralWidget(self._window.webview)
        self._window.resize(600, 700)
        self._window.show()

    def _handle_login_load_finished(self):
        def callback(result):
            self._window.webview.load(QUrl.fromUserInput(result))
            self._window.webview.loadFinished.connect(self._handle_project_load_finished)

        if self._window.webview.url().toString() == PROJECT_URL:
            self._window.webview.page().runJavaScript(JAVASCRIPT_PROJECT_PATH_EXTRACTOR, 0, callback)

    def _handle_project_load_finished(self):
        def callback(result):
            self._csrf = result
            self._login_success = True
            QCoreApplication.quit()
        
        self._window.webview.page().runJavaScript(JAVASCRIPT_CSRF_EXTRACTOR, 0, callback)

    def _handle_cookie_added(self, cookie):
        cookie_name = cookie.name().data().decode('utf-8')
        if cookie_name in COOKIE_NAMES:
            self._cookies[cookie_name] = cookie.value().data().decode('utf-8')

    def login(self):
        QLoggingCategory.setFilterRules('qt.webenginecontext.info=false')

        app = QApplication([])
        self._create_main_window()
        app.exec()

        if not self._login_success:
            return None

        return {"cookie": self._cookies, "csrf": self._csrf}
