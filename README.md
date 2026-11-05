Anki addon: minimize to tray
=========================================================
Adds an icon to the system tray and allows minimizing anki to the tray when the icon is pressed or when the main window X button is pressed.

Platform Support
================
This addon is primarily developed and tested on **Linux**.

**Windows support is limited** due to platform-specific bugs that are often difficult to debug. Many of these issues appear to be caused by upstream problems in Qt or Anki's Windows implementation. If you encounter issues on Windows, please check the [issue tracker](https://github.com/simgunz/anki21-addons_minimize-to-tray/issues) for known problems and workarounds.

Flatpak
=======
The Flatpak version of Anki has no access to the system tray, so the addon works with some limits:

- The tray icon only appears while Anki is hidden, and goes away when Anki is open.
- To hide Anki, close its window. Clicking the tray icon can only open Anki.
- If you don't see a tray icon, open Anki from your applications menu to bring it back.
- To quit, open Anki and use *File > Exit*. Quit in the tray icon's menu force-closes Anki.

To get the full tray icon, run this command in a terminal and restart Anki:

```
flatpak override --user --talk-name=org.kde.StatusNotifierWatcher net.ankiweb.Anki
```

Configuration
=============
- To start Anki minimized in the tray, go to *Tools > Add-ons > Minimize to tray > Config* and set `hide_on_startup` to `true`
- To enable debug mode (for troubleshooting), set `debug` to `true` in the same config menu. Debug messages will be printed to the console.

Author
======
Simone Gaiarin \<simgunz AT gmail DOT com\>

License
=======
Software distributed under the GNU General Public License version 3 (GNU GPL v3).

http://www.gnu.org/copyleft/gpl.html

References
=============
- [Anki addon page](https://ankiweb.net/shared/info/85158043)

