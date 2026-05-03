#!/usr/bin/env python3

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, GLib, Gio

from splash import SplashScreen
from window import MainWindow
from server import emit_log


class App(Gtk.Application):

    def __init__(self):
        super().__init__(
            application_id="com.github.gabutakut.gabutytb",
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )
        self.win = None
        self.splash = None
        self._auto_start = False

        entry = GLib.OptionEntry()
        entry.long_name = "startingup"
        entry.short_name = ord('s')
        entry.flags = 0
        entry.arg = 0
        entry.arg_data = None
        entry.description = "Run App on Startup"
        entry.arg_description = None
        self.add_main_option_entries([entry])

        self.connect("activate",             self._on_activate)
        self.connect("handle-local-options", self._on_handle_options)

    def _on_handle_options(self, app, options_dict):
        if options_dict.contains("startingup"):
            self._auto_start = True
        return -1

    def _on_activate(self, app):
        if self.win is not None:
            self.win.present()
            return

        if self.splash is None:
            self.splash = SplashScreen(app)
            self.splash.present()
            step = [0]

            def _progress():
                step[0] += 1
                frac = step[0] / 5
                self.splash.set_status(f"Loading... {step[0]}:5", fraction=frac)
                if step[0] >= 5:
                    self.splash.set_status("Ready! ✓", fraction=1.0)

                    def show_main():
                        self.splash.close()
                        if self.win is None:
                            self.win = MainWindow(app)
                            self.win.connect("close-request", self._on_main_close)
                            self.gbtytb_autostart(True)
                        if self._auto_start:
                            self._auto_start = False
                            self.win._on_start(None)
                        else:
                            self.win.present()
                        return False

                    GLib.timeout_add(500, show_main)
                    return False
                return True

            GLib.timeout_add(150, _progress)

    def _on_main_close(self, window):
        self.win.hide()
        if self.win.props.hide_on_close:
            return

        splash = SplashScreen(self)
        splash.present()
        step = [0]

        def _progress():
            step[0] += 1
            splash.set_status(f"Saving {step[0]}:5", fraction=step[0] / 5)
            if step[0] >= 5:
                splash.set_status("Good Bye! ✓", fraction=1.0)

                def close_main():
                    splash.close()
                    self.quit()
                    return False

                GLib.timeout_add(500, close_main)
                return False
            return True

        GLib.timeout_add(150, _progress)
        return False

    def gbtytb_autostart(self, enabled: bool):

        def _on_bus_ready(source, result):
            try:
                connection = Gio.bus_get_finish(result)
            except Exception as e:
                emit_log("ERROR", f"DBus bus failed: {e}")
                return

            for cmd in (
                ["flatpak", "run", "com.github.gabutakut.gabutytb", "-s"],
                ["com.github.gabutakut.gabutytb", "-s"],
            ):
                params = GLib.Variant("(sa{sv})", ( "", { "reason": GLib.Variant("s",  "Auto start GabutYTB"), "autostart": GLib.Variant("b",  enabled), "commandline": GLib.Variant("as", cmd), "dbus-activatable": GLib.Variant("b", False), },),)
                connection.call(
                    "org.freedesktop.portal.Desktop",
                    "/org/freedesktop/portal/desktop",
                    "org.freedesktop.portal.Background",
                    "RequestBackground",
                    params, None,
                    Gio.DBusCallFlags.NONE, -1, None,
                    _on_call_done,
                )

        def _on_call_done(source, result):
            try:
                source.call_finish(result)
                status = "actived" if enabled else "disabled"
                emit_log("SERVER", f"✅ Autostart {status}")
            except Exception as e:
                emit_log("ERROR", f"Portal autostart failed: {e}")

        Gio.bus_get(Gio.BusType.SESSION, None, _on_bus_ready)

if __name__ == "__main__":
    app = App()
    sys.exit(app.run(sys.argv))
