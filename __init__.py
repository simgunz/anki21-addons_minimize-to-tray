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


def onFocusChanged(self, old, now):
    """Keep track of the focused window in order to refocus it on showAll
    """
    if now is not None:
        self.last_focus = now

def showWindows(self, windows):
    for w in windows:
        if w.obj.isWindow():
            w.obj.show()
            w.obj.setWindowState(w.state)

def showAll(self):
    """Show all windows
    """
    if self.anki_visible:
        self.showWindows(self.visibleWindows())
    else:
        self.showWindows(self.tray_hidden)
    self.last_focus.activateWindow()
    self.anki_visible = True

def hideAll(self):
    """Hide all windows
    """
    self.tray_hidden = []
    windows = self.visibleWindows()
    for w in windows:
        w.obj.hide()
    self.tray_hidden = windows
    self.anki_visible = False

def visibleWindows(self):
    windows = []
    for w in QApplication.topLevelWidgets():
        if w.isWindow() and not w.isHidden():
            if not w.children():
                continue
            statefulWindow = Window(w, w.windowState())
            windows.append(statefulWindow)
    return windows

def trayActivated(self, reason):
    """Show/hide all Anki windows when the tray icon is clicked
    """
    if reason == QSystemTrayIcon.Trigger:
        self.showAll()

def createSysTray(self):
    """Create an system tray with the Anki icon
    """
    # Check if self (i.e., mw.aqt) already has a trayIcon
    if hasattr(self, 'trayIcon'):
        return
    self.anki_visible = True
    self.last_focus = self
    self.trayIcon = QSystemTrayIcon(self)
    ankiLogo = QIcon()
    ankiLogo.addPixmap(QPixmap(":/icons/anki.png"), QIcon.Normal, QIcon.Off)
    self.trayIcon.setIcon(QIcon.fromTheme("anki", ankiLogo))
    trayMenu = QMenu(self)
    self.trayIcon.setContextMenu(trayMenu)
    showAction = trayMenu.addAction("Show all windows")
    showAction.triggered.connect(self.showAll)
    trayMenu.addAction(self.form.actionExit)
    self.trayIcon.activated.connect(self.trayActivated)
    self.app.focusChanged.connect(self.onFocusChanged)
    self.trayIcon.show()

def minimizeToTrayClose(self):
    self.closeEventFromAction = True
    self.close()

def wrapCloseCloseEvent():
    "Override an existing method of an instnce of an object"
    def repl(self, event):
        if not self.closeEventFromAction:
            #self.col.save()
            self.hideAll()
            event.ignore()
            return
        AnkiQt.closeEvent(self, event)
    return MethodType(repl, mw)

def minimizeToTrayInit():
    if hasattr(mw, 'trayIcon'):
        return
    mw.closeEventFromAction = False
    mw.createSysTray()
    # Disconnecting from close may have some side effects (e.g. QApplication::lastWindowClosed() signal not emitted)
    mw.form.actionExit.triggered.disconnect(mw.close)
    mw.form.actionExit.triggered.connect(mw.minimizeToTrayClose)
    config = mw.addonManager.getConfig(__name__) # Get addon config
    if config['hide_on_startup']:
        mw.hideAll()

# Set Anki main window new methods
mw.onFocusChanged = MethodType(onFocusChanged, mw)
mw.showWindows = MethodType(showWindows, mw)
mw.showAll = MethodType(showAll, mw)
mw.hideAll = MethodType(hideAll, mw)
mw.visibleWindows = MethodType(visibleWindows, mw)
mw.trayActivated = MethodType(trayActivated, mw)
mw.createSysTray = MethodType(createSysTray, mw)

mw.minimizeToTrayClose = MethodType(minimizeToTrayClose, mw)
mw.closeEvent = wrapCloseCloseEvent()

hooks.addHook("profileLoaded", minimizeToTrayInit)
