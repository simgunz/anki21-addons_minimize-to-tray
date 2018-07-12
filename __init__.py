#-*- coding: utf-8 -*-
# Copyright: Simone Gaiarin <simgunz@gmail.com>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
# Name: Minimize to Tray 2
# Version: 0.2
# Description: Minimize anki to tray when the X button is pressed (Anki 2 version)
# Homepage: https://github.com/simgunz/anki-plugins
# Report any problem in the github issues section

from types import MethodType

from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from anki import hooks
from aqt import mw              #mw is the INSTANCE of the main window (aqt/main.py) create in aqt/__init__
from aqt.main import AnkiQt

def onFocusChanged(self, old, now):
    """Keep track of the focused window in order to refocus it on showAll
    """
    if now == None:
        self.last_focus = old

def showAll(self):
    """Show all windows
    """
    for w in self.tray_hidden:
        if w.isWindow() and w.isHidden():
            w.showNormal()
    active = self.last_focus
    active.raise_()
    active.activateWindow()
    self.anki_visible = True
    self.tray_hidden = []

def hideAll(self):
    """Hide all windows
    """
    self.tray_hidden = []
    for w in QApplication.topLevelWidgets():
        if w.isWindow() and not w.isHidden():
            if not w.children():
                continue
            w.hide()
            self.tray_hidden.append(w)
    self.anki_visible = False

def trayActivated(self, reason):
    """Show/hide all Anki windows when the tray icon is clicked
    """
    if reason == QSystemTrayIcon.Trigger:
        if self.anki_visible:
            self.hideAll()
        else:
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
    self.trayIcon.setIcon(ankiLogo)
    trayMenu = QMenu(self)
    self.trayIcon.setContextMenu(trayMenu)
    trayMenu.addAction(self.form.actionExit)
    self.trayIcon.activated.connect(self.trayActivated)
    self.app.focusChanged.connect(self.onFocusChanged)
    self.trayIcon.show()

def minimizeToTrayInit():
    if hasattr(mw, 'trayIcon'):
        return
    mw.createSysTray()
    config = mw.addonManager.getConfig(__name__) # Get addon config
    if config['hide_on_startup']:
        mw.hideAll()


# Set Anki main window new methods
mw.onFocusChanged = MethodType(onFocusChanged, mw) 
mw.showAll = MethodType(showAll, mw) 
mw.hideAll = MethodType(hideAll, mw) 
mw.trayActivated = MethodType(trayActivated, mw) 
mw.createSysTray = MethodType(createSysTray, mw) 

hooks.addHook("profileLoaded", minimizeToTrayInit)
