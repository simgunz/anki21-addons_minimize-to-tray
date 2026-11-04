# -*- coding: utf-8 -*-
# Copyright: Simone Gaiarin <simgunz@gmail.com>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
# Name: Minimize to Tray 2
# Version: 0.2
# Description: Minimize anki to tray when the X button is pressed (Anki 2 version)
# Homepage: https://github.com/simgunz/anki-plugins
# Report any problem in the github issues section
import sys
from pathlib import Path
from types import MethodType

from aqt.qt import (
    sip,
    Qt,
    QIcon,
    QPixmap,
    QApplication,
    QCheckBox,
    QMenu,
    QMessageBox,
    QSystemTrayIcon,
)

from aqt import gui_hooks, mw  # mw is the INSTANCE of the main window
from aqt.main import AnkiQt

FLATPAK_TRAY_WARNING = """\
<p>You installed Anki as a Flatpak, so Minimize to tray works with some limits:</p>
<ul>
<li>The tray icon only appears while Anki is hidden, and goes away when Anki is open.</li>
<li>To hide Anki, close its window. Clicking the tray icon can only open Anki.</li>
<li>If you don't see a tray icon, open Anki from your applications menu to bring it back.</li>
<li>To quit, open Anki and use File > Exit. Quit in the tray icon's menu force-closes Anki.</li>
</ul>
<p>To get the full tray icon, run this command in a terminal and restart Anki:</p>
<p><code>flatpak override --user --talk-name=org.kde.StatusNotifierWatcher net.ankiweb.Anki</code></p>
"""


class AnkiSystemTray:
    def _debug_print(self, message):
        """Helper function to print debug messages when debug mode is enabled."""
        if self.debug:
            print(f"[MinimizeToTray] DEBUG: {message}")

    def __init__(self, mw):
        """Create a system tray with the Anki icon."""
        self.mw = mw
        config = self.mw.addonManager.getConfig(__name__)
        self.debug = config.get("debug", False)

        self._debug_print("Initializing AnkiSystemTray")

        self.isAnkiFocused = True
        self.isMinimizedToTray = False
        self.lastFocusedWidget = mw
        self.explicitlyHiddenWindows = []
        self.windowVisibilitySnapshot = {}

        self._debug_print("Creating tray icon")
        self.trayIcon = self._createTrayIcon()

        QApplication.setQuitOnLastWindowClosed(False)
        self._configureMw()
        self.trayIcon.show()

        self._debug_print(
            f"Configuration: hide_on_startup={config.get('hide_on_startup', False)}, debug={self.debug}"
        )

        self._warnIfFlatpakTrayUnavailable(config)

        if config["hide_on_startup"]:
            self._debug_print("Hiding all windows on startup")
            self.hideAll()

    def onActivated(self, reason):
        """Show/hide all Anki windows when the tray icon is clicked.

        The windows are shown if:
        - anki window is not in focus
        - any window is minimized
        - anki is minimize to tray
        The windows are hidden otherwise.

        The focus cannot be detected given that the main window focus is lost before this
        slot is activated. For this reason and to prevent that anki is minimized when not
        focused, on Windows are the windows are never hidden.
        """
        self._debug_print(f"Tray icon activated with reason: {reason}")

        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            should_show = (
                not self.isAnkiFocused
                or self._anyWindowMinimized()
                or self.isMinimizedToTray
            )

            self._debug_print(
                f"Decision factors: isAnkiFocused={self.isAnkiFocused}, anyWindowMinimized={self._anyWindowMinimized()}, isMinimizedToTray={self.isMinimizedToTray}"
            )
            self._debug_print(f"Should show: {should_show}")

            if should_show:
                self.showAll()
            elif not sys.platform.startswith("win32"):
                self._debug_print("Platform is not Windows, hiding all windows")
                self.hideAll()

    def onFocusChanged(self, old, now):
        """Keep track of the focused window in order to refocus it on showAll."""
        self.isAnkiFocused = now is not None
        self._debug_print(
            f"Focus changed: old={old}, now={now}, isAnkiFocused={self.isAnkiFocused}"
        )
        if self.isAnkiFocused:
            self.lastFocusedWidget = now
            self._debug_print(f"Updated lastFocusedWidget to: {now}")

    def onExit(self):
        self._debug_print("Exit action triggered")
        self.mw.closeEventFromAction = True
        self.mw.close()

    def onAppMsg(self, buf):
        """Show the windows when Anki is launched again while minimized to tray.

        Workaround for Flatpak without access to org.kde.StatusNotifierWatcher: the
        add-on's tray icon cannot register, so Plasma shows a background app icon that
        launches Anki again when clicked. Anki only raises the main window on a new
        launch, which has no effect on a hidden window.
        """
        self._debug_print(
            f"App message received: {buf}, isMinimizedToTray={self.isMinimizedToTray}"
        )
        if self.isMinimizedToTray:
            self.showAll()

    def showAll(self):
        """Show all windows."""
        self._debug_print(
            f"Showing all windows. isMinimizedToTray={self.isMinimizedToTray}"
        )

        if self.isMinimizedToTray:
            windows_to_show = [
                w for w in self.explicitlyHiddenWindows if not sip.isdeleted(w)
            ]
            self._debug_print(
                f"Showing explicitly hidden windows: {len(windows_to_show)} windows"
            )
            self._showWindows(windows_to_show)
            self._restoreWindowStates()
        else:
            visible_windows = self._visibleWindows()
            self._debug_print(
                f"Showing visible windows: {len(visible_windows)} windows"
            )
            self._showWindows(visible_windows)

        if not sip.isdeleted(self.lastFocusedWidget):
            self._debug_print(
                f"Raising and activating last focused widget: {self.lastFocusedWidget}"
            )
            self.lastFocusedWidget.raise_()
            self.lastFocusedWidget.activateWindow()
        else:
            self._debug_print("Last focused widget has been deleted")

        self.isMinimizedToTray = False

    def hideAll(self):
        """Hide all windows."""
        self._snapshotWindowStates()
        self.explicitlyHiddenWindows = self._visibleWindows()
        self._debug_print(
            f"Hiding all windows: {len(self.explicitlyHiddenWindows)} windows to hide"
        )

        for w in self.explicitlyHiddenWindows:
            self._debug_print(f"Hiding window: {w}")
            w.hide()

        self.isMinimizedToTray = True
        self._debug_print("All windows hidden, set isMinimizedToTray=True")

    def _showWindows(self, windows):
        self._debug_print(f"_showWindows called with {len(windows)} windows")

        for w in windows:
            if sip.isdeleted(w):
                self._debug_print(f"Skipping deleted window: {w}")
                continue

            if w.isMinimized() == Qt.WindowState.WindowMinimized:
                self._debug_print(f"Restoring minimized window: {w}")
                # Windows that were maximized are not restored maximized unfortunately
                w.showNormal()
            else:
                self._debug_print(f"Showing window with hide/show hack: {w}")
                # hide(): hack that solves two problems:
                # 1. focus the windows after TWO other non-Anki windows
                # gained focus (Qt bug?). Causes a minor flicker when the
                # Anki windows are already visible.
                # 2. allows avoiding to call activateWindow() on each
                # windows in order to raise them above non-Anki windows
                # and thus avoid breaking the restore-last-focus mechanism
                w.hide()
                w.show()
            w.raise_()

    def _visibleWindows(self):
        """Return the windows actually visible Anki windows.

        Anki has some hidden windows and menus that we should ignore.
        """
        windows = []
        all_widgets = QApplication.topLevelWidgets()

        self._debug_print(
            f"Checking {len(all_widgets)} top level widgets for visible windows"
        )

        for w in all_widgets:
            if w.isWindow() and not w.isHidden():
                if not w.children():
                    self._debug_print(f"Skipping window with no children: {w}")
                    continue
                windows.append(w)
                self._debug_print(f"Found visible window: {w}")
            else:
                self._debug_print(
                    f"Skipping non-window or hidden widget: {w} (isWindow={w.isWindow()}, isHidden={w.isHidden()})"
                )

        self._debug_print(f"Found {len(windows)} visible windows")
        return windows

    def _anyWindowMinimized(self):
        visible_windows = self._visibleWindows()
        minimized_windows = [
            w
            for w in visible_windows
            if w.windowState() == Qt.WindowState.WindowMinimized
        ]

        self._debug_print(
            f"Checking for minimized windows: {len(minimized_windows)} out of {len(visible_windows)} are minimized"
        )

        return len(minimized_windows) > 0

    def _snapshotWindowStates(self):
        """Capture the visibility state of all top-level windows.

        This is a workaround for unexpected Qt behavior: when restoring windows
        from tray, previously-closed child dialog windows sometimes reappear.

        The root cause is unclear - possibly related to the hide/show hack in
        _showWindows(), or general Qt parent-child window behavior, or something else.

        By snapshotting window states before hiding, we can restore the exact
        visibility state after showing windows from tray.
        """
        self.windowVisibilitySnapshot = {}
        all_widgets = QApplication.topLevelWidgets()

        for w in all_widgets:
            if w.isWindow() and w.children():
                self.windowVisibilitySnapshot[w] = not w.isHidden()
                self._debug_print(
                    f"Snapshotting window {w}: visible={self.windowVisibilitySnapshot[w]}"
                )

    def _restoreWindowStates(self):
        """Restore window visibility to match the pre-minimize snapshot.

        This prevents child windows (e.g., Custom Study dialog, Update Add-ons)
        from reappearing after they were closed by the user.

        The exact cause is unknown, but empirically, some child dialogs become
        visible again after showing the parent window. This function corrects
        that by enforcing the visibility state from before minimization.
        """
        self._debug_print("Restoring window visibility from snapshot")

        for w, was_visible in self.windowVisibilitySnapshot.items():
            if sip.isdeleted(w):
                continue

            is_currently_visible = not w.isHidden()
            if is_currently_visible and not was_visible:
                self._debug_print(
                    f"Hiding window that should not be visible: {w} (was {was_visible}, now {is_currently_visible})"
                )
                w.hide()
            elif not is_currently_visible and was_visible:
                self._debug_print(
                    f"Showing window that should be visible: {w} (was {was_visible}, now {is_currently_visible})"
                )
                w.show()

    def _warnIfFlatpakTrayUnavailable(self, config):
        """Explain the Flatpak tray limits until the user dismisses the warning."""
        isFlatpak = Path("/.flatpak-info").exists()
        isTrayAvailable = QSystemTrayIcon.isSystemTrayAvailable()
        isDismissed = config.get("flatpak_tray_warning_dismissed", False)
        self._debug_print(
            f"Flatpak tray check: isFlatpak={isFlatpak}, isTrayAvailable={isTrayAvailable}, isDismissed={isDismissed}"
        )

        if not isFlatpak or isTrayAvailable or isDismissed:
            return

        messageBox = QMessageBox(self.mw)
        messageBox.setIcon(QMessageBox.Icon.Warning)
        messageBox.setWindowTitle("Minimize to tray")
        messageBox.setTextFormat(Qt.TextFormat.RichText)
        messageBox.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        messageBox.setText(FLATPAK_TRAY_WARNING)
        dontShowAgain = QCheckBox("Don't show this again")
        messageBox.setCheckBox(dontShowAgain)
        messageBox.exec()

        if dontShowAgain.isChecked():
            config["flatpak_tray_warning_dismissed"] = True
            self.mw.addonManager.writeConfig(__name__, config)

    def _createTrayIcon(self):
        self._debug_print("Creating system tray icon")

        trayIcon = QSystemTrayIcon(self.mw)
        ankiLogo = QIcon()
        ankiLogo.addPixmap(
            QPixmap("icons:anki.png"), QIcon.Mode.Normal, QIcon.State.Off
        )
        trayIcon.setIcon(QIcon.fromTheme("anki", ankiLogo))

        self._debug_print("Setting up tray menu")
        trayMenu = QMenu(self.mw)
        trayIcon.setContextMenu(trayMenu)
        showAction = trayMenu.addAction("Show all windows")
        showAction.triggered.connect(self.showAll)
        trayMenu.addAction(self.mw.form.actionExit)
        trayIcon.activated.connect(self.onActivated)

        self._debug_print("Tray icon created successfully")
        return trayIcon

    def _configureMw(self):
        self._debug_print("Configuring main window")

        self.mw.closeEventFromAction = False
        self.mw.app.focusChanged.connect(self.onFocusChanged)
        self.mw.app.appMsg.connect(self.onAppMsg)

        self._debug_print("Disconnecting and reconnecting exit action")
        # Disconnecting from close may have some side effects
        # (e.g. QApplication::lastWindowClosed() signal not emitted)
        self.mw.form.actionExit.triggered.disconnect(self.mw.close)
        self.mw.form.actionExit.triggered.connect(self.onExit)

        self._debug_print("Wrapping close event")
        self.mw.closeEvent = self._wrapCloseCloseEvent()

    def _wrapCloseCloseEvent(self):
        """Override the close method of the mw instance."""

        def repl(self, event):
            self.systemTray._debug_print(
                f"Close event triggered: closeEventFromAction={self.closeEventFromAction}"
            )

            if self.closeEventFromAction:
                self.systemTray._debug_print(
                    "Exit action was used, performing normal close"
                )
                AnkiQt.closeEvent(self, event)
            else:
                self.systemTray._debug_print(
                    "X button was pressed, hiding to tray instead"
                )
                self.systemTray.hideAll()
                event.ignore()

        return MethodType(repl, self.mw)


def minimizeToTrayInit():
    if hasattr(mw, "trayIcon"):
        return

    config = mw.addonManager.getConfig(__name__)
    debug = config.get("debug", False)

    if debug:
        print("[MinimizeToTray] DEBUG: Initializing Minimize to Tray addon")

    mw.systemTray = AnkiSystemTray(mw)


gui_hooks.main_window_did_init.append(minimizeToTrayInit)
