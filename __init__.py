#-*- coding: utf-8 -*-
# Copyright: Simone Gaiarin <simgunz@gmail.com>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
# Name: Minimize to Tray 2
# Version: 0.2
# Description: Minimize anki to tray when the X button is pressed (Anki 2 version)
# Homepage: https://github.com/simgunz/anki-plugins
# Report any problem in the github issues section

from types import MethodType
from typing import NamedTuple

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QWidget, QApplication, QMenu, QSystemTrayIcon

from anki import hooks
from aqt import mw              #mw is the INSTANCE of the main window (aqt/main.py) create in aqt/__init__
from aqt.main import AnkiQt


class Window(NamedTuple):
    obj: QWidget
    state: Qt.WindowState


class AnkiSystemTray():
    def __init__(self, mw):
        """Create a system tray with the Anki icon."""
        self.mw = mw
        self.anki_visible = True
        self.last_focus = mw
        self.trayIcon = self._createTrayIcon()
        self._configureMw()
        self.trayIcon.show()
        config = self.mw.addonManager.getConfig(__name__)
        if config['hide_on_startup']:
            self.hideAll()

    def _configureMw(self):
        self.mw.closeEventFromAction = False
        self.mw.app.focusChanged.connect(self.onFocusChanged)
        # Disconnecting from close may have some side effects
        # (e.g. QApplication::lastWindowClosed() signal not emitted)
        self.mw.form.actionExit.triggered.disconnect(self.mw.close)
        self.mw.form.actionExit.triggered.connect(self.onClose)
        self.mw.closeEvent = self._wrapCloseCloseEvent()

    def trayActivated(self, reason):
        """Show/hide all Anki windows when the tray icon is clicked
        """
        if reason == QSystemTrayIcon.Trigger:
            self.showAll()

    def onFocusChanged(self, old, now):
        """Keep track of the focused window in order to refocus it on showAll
        """
        if now is not None:
            self.last_focus = now

    def onClose(self):
        self.mw.closeEventFromAction = True
        self.mw.close()

    def showAll(self):
        """Show all windows
        """
        if self.anki_visible:
            self._showWindows(self._visibleWindows())
        else:
            self._showWindows(self.tray_hidden)
        self.last_focus.activateWindow()
        self.last_focus.raise_()
        self.anki_visible = True

    def hideAll(self):
        """Hide all windows
        """
        self.tray_hidden = []
        windows = self._visibleWindows()
        for w in windows:
            w.obj.hide()
        self.tray_hidden = windows
        self.anki_visible = False

    def _showWindows(self, windows):
        for w in windows:
            if w.obj.isWindow():
                if w.state == Qt.WindowMinimized:
                    w.obj.showNormal()
                else:
                    w.obj.show()
                    w.obj.setWindowState(w.state)
                w.obj.raise_()

    def _visibleWindows(self):
        windows = []
        for w in QApplication.topLevelWidgets():
            if w.isWindow() and not w.isHidden():
                if not w.children():
                    continue
                statefulWindow = Window(w, w.windowState())
                windows.append(statefulWindow)
        return windows

    def _createTrayIcon(self):
        trayIcon = QSystemTrayIcon(self.mw)
        ankiLogo = QIcon()
        ankiLogo.addPixmap(QPixmap(":/icons/anki.png"), QIcon.Normal, QIcon.Off)
        trayIcon.setIcon(QIcon.fromTheme("anki", ankiLogo))
        trayMenu = QMenu(self.mw)
        trayIcon.setContextMenu(trayMenu)
        showAction = trayMenu.addAction("Show all windows")
        showAction.triggered.connect(self.showAll)
        trayMenu.addAction(self.mw.form.actionExit)
        trayIcon.activated.connect(self.trayActivated)
        return trayIcon

    def _wrapCloseCloseEvent(self):
        "Override an existing method of an instance of an object"
        def repl(self, event):
            if self.closeEventFromAction:
                # The 'Exit' action in the sys tray context menu was activated
                AnkiQt.closeEvent(self, event)
            else:
                # The main window X button was pressed
                #self.col.save()
                self.systemTray.hideAll()
                event.ignore()
        return MethodType(repl, self.mw)


def minimizeToTrayInit():
    if hasattr(mw, 'trayIcon'):
        return
    mw.systemTray = AnkiSystemTray(mw)


hooks.addHook("profileLoaded", minimizeToTrayInit)
