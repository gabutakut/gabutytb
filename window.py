#!/usr/bin/env python3

import os
import json
from datetime import datetime

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib, Gdk, Pango

from server import (
    ServerManager, emit_log, set_log_callback,
    set_proxy, get_proxy,
    set_cookies_browser, get_cookies_browser,
    HAS_YTDLP,
)

CSS = """
window { background-color: #0f1117; }
.toggle-row { margin-top: 4px; margin-bottom: 2px; }
.toggle-label { font-size: 10px; color: #8b949e; font-family: monospace; }
.toggle-on  { color: #3fb950; font-size: 10px; font-family: monospace; font-weight: bold; }
.toggle-off { color: #6e7681; font-size: 10px; font-family: monospace; }
.sidebar { background-color: #161b22; border-right: 1px solid #30363d; padding: 16px 12px; }
.brand-label { font-family: monospace; font-size: 16px; font-weight: 800; color: #58a6ff; }
.port-label { font-size: 10px; color: #8b949e; font-family: monospace; margin-top: 8px; }
.port-entry { background-color: #0d1117; color: #e6edf3; border: 1px solid #30363d; border-radius: 6px; padding: 6px; }
.btn-start { background-color: #238636; color: white; border-radius: 6px; font-weight: bold; margin-top: 12px; padding: 8px; }
.btn-stop { background-color: #b62324; color: white; border-radius: 6px; font-weight: bold; margin-top: 8px; padding: 8px; }
.btn-clear { background-color: #238636; color: white; border-radius: 6px; font-weight: bold; margin-top: 12px; padding: 8px; }
.status-dot-on { color: #3fb950; font-size: 11px; font-weight: bold; }
.status-dot-off { color: #6e7681; font-size: 11px; }
.stat-box { background-color: #0d1117; border: 1px solid #21262d; border-radius: 8px; padding: 10px; margin-top: 16px; }
.stat-number { font-family: monospace; font-size: 20px; font-weight: bold; color: #58a6ff; }
.stat-label { font-size: 9px; color: #6e7681; font-family: monospace; }
.log-header { background-color: #161b22; border-bottom: 1px solid #30363d; padding: 10px 16px; }
.log-title { font-family: monospace; font-size: 12px; color: #8b949e; letter-spacing: 1px; }
"""

BROWSERS = ["", "chrome", "firefox", "edge", "chromium", "brave", "opera", "safari", "vivaldi"]
BROWSER_LABELS = ["None", "Chrome", "Firefox", "Edge", "Chromium", "Brave", "Opera", "Safari", "Vivaldi"]

CONFIG_PATH = os.path.expanduser("~/.config/gabutytb/config.json")


def load_config() -> dict:
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r") as f:
                return json.load(f)
    except Exception as e:
        emit_log("ERROR", f"Failed load config: {e}")
    return {"port": "3030", "proxy": "", "proxy_enabled": False, "cookies_browser": ""}


def save_config(port: str, proxy: str, proxy_enabled: bool = False, cookies_browser: str = ""):
    try:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump({
                "port": port,
                "proxy": proxy,
                "proxy_enabled": proxy_enabled,
                "cookies_browser": cookies_browser,
            }, f, indent=2)
        emit_log("SERVER", f"✅ Config saved → {CONFIG_PATH}")
    except Exception as e:
        emit_log("ERROR", f"Failed savig config: {e}")


class MainWindow(Gtk.ApplicationWindow):

    def __init__(self, app):
        super().__init__(application=app, title="Gabut Plugin Youtube, Etc")
        self.set_size_request(800, 500)

        self._server_mgr = ServerManager()
        self._req_count = 0
        self._err_count = 0

        set_log_callback(self._on_log)
        self._build_ui()
        self._apply_css()
        self._load_config()

    def _apply_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _load_config(self):
        cfg = load_config()
        self._port_entry.set_text(cfg.get("port", "3030"))
        self._proxy_entry.set_text(cfg.get("proxy", ""))

        proxy_enabled = cfg.get("proxy_enabled", False)
        self._proxy_switch.set_active(proxy_enabled)

        if proxy_enabled:
            self._proxy_status_lbl.set_text("ON")
            self._proxy_status_lbl.add_css_class("toggle-on")
        else:
            self._proxy_status_lbl.set_text("OFF")
            self._proxy_status_lbl.add_css_class("toggle-off")

        browser = cfg.get("cookies_browser", "")
        set_cookies_browser(browser)
        idx = BROWSERS.index(browser) if browser in BROWSERS else 0
        self._browser_dropdown.set_selected(idx)

        emit_log("SERVER", f"📂 Config loaded | port={cfg.get('port')} proxy={'ON' if proxy_enabled else 'OFF'} browser={browser or 'none'}")

    def _build_ui(self):
        root = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.set_child(root)

        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sidebar.add_css_class("sidebar")
        root.append(sidebar)

        brand = Gtk.Label(label="JSON-RPC SERVER")
        brand.add_css_class("brand-label")
        brand.set_halign(Gtk.Align.START)
        sidebar.append(brand)

        sep1 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep1.set_margin_top(12)
        sep1.set_margin_bottom(4)
        sidebar.append(sep1)

        status_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        status_row.set_margin_top(6)
        self._status_dot = Gtk.Label(label="● OFFLINE")
        self._status_dot.add_css_class("status-dot-off")
        status_row.append(self._status_dot)
        sidebar.append(status_row)

        proxy_lbl = Gtk.Label(label="PROXY  (opsional)")
        proxy_lbl.add_css_class("port-label")
        proxy_lbl.set_halign(Gtk.Align.START)
        sidebar.append(proxy_lbl)

        self._proxy_entry = Gtk.Entry()
        self._proxy_entry.set_placeholder_text("socks5://127.0.0.1:1080")
        self._proxy_entry.add_css_class("port-entry")
        sidebar.append(self._proxy_entry)

        toggle_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        toggle_row.add_css_class("toggle-row")

        toggle_lbl = Gtk.Label(label="Use Proxy")
        toggle_lbl.add_css_class("toggle-label")
        toggle_lbl.set_halign(Gtk.Align.START)

        self._proxy_switch = Gtk.Switch()
        self._proxy_switch.set_active(False)
        self._proxy_switch.connect("notify::active", self._on_proxy_toggle)

        self._proxy_status_lbl = Gtk.Label(label="OFF")
        self._proxy_status_lbl.add_css_class("toggle-off")

        toggle_row.append(toggle_lbl)
        toggle_row.append(self._proxy_switch)
        toggle_row.append(self._proxy_status_lbl)
        sidebar.append(toggle_row)


        browser_lbl = Gtk.Label(label="COOKIES FROM BROWSER")
        browser_lbl.add_css_class("port-label")
        browser_lbl.set_halign(Gtk.Align.START)
        sidebar.append(browser_lbl)

        browser_store = Gtk.StringList.new(BROWSER_LABELS)
        self._browser_dropdown = Gtk.DropDown(model=browser_store)
        self._browser_dropdown.set_selected(0)
        self._browser_dropdown.connect("notify::selected", self._on_browser_changed)
        sidebar.append(self._browser_dropdown)

        port_lbl = Gtk.Label(label="Listen PORT")
        port_lbl.add_css_class("port-label")
        port_lbl.set_halign(Gtk.Align.START)
        sidebar.append(port_lbl)

        self._port_entry = Gtk.Entry()
        self._port_entry.set_text("3030")
        self._port_entry.add_css_class("port-entry")
        sidebar.append(self._port_entry)

        self._btn_start = Gtk.Button(label="▶  START SERVER")
        self._btn_start.add_css_class("btn-start")
        self._btn_start.connect("clicked", self._on_start)
        sidebar.append(self._btn_start)

        self._btn_stop = Gtk.Button(label="■  STOP SERVER")
        self._btn_stop.add_css_class("btn-stop")
        self._btn_stop.connect("clicked", self._on_stop)
        self._btn_stop.set_sensitive(False)
        sidebar.append(self._btn_stop)

        btn_clear = Gtk.Button(label="⌫  CLEAR LOG")
        btn_clear.add_css_class("btn-clear")
        btn_clear.connect("clicked", self._on_clear)
        sidebar.append(btn_clear)

        stats_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        stats_box.add_css_class("stat-box")

        req_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._lbl_req = Gtk.Label(label="0")
        self._lbl_req.add_css_class("stat-number")
        lbl_req_txt = Gtk.Label(label="REQUESTS")
        lbl_req_txt.add_css_class("stat-label")
        lbl_req_txt.set_valign(Gtk.Align.END)
        lbl_req_txt.set_margin_bottom(4)
        req_row.append(self._lbl_req)
        req_row.append(lbl_req_txt)
        stats_box.append(req_row)

        err_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._lbl_err = Gtk.Label(label="0")
        self._lbl_err.add_css_class("stat-number")
        self._lbl_err.set_markup('<span foreground="#f85149">0</span>')
        lbl_err_txt = Gtk.Label(label="ERRORS")
        lbl_err_txt.add_css_class("stat-label")
        lbl_err_txt.set_valign(Gtk.Align.END)
        lbl_err_txt.set_margin_bottom(4)
        err_row.append(self._lbl_err)
        err_row.append(lbl_err_txt)
        stats_box.append(err_row)

        sidebar.append(stats_box)

        if not HAS_YTDLP:
            emit_log("ERROR", "⚠no installed yt-dlp Please Install! pip install yt-dlp")

        spacer = Gtk.Box()
        spacer.set_vexpand(True)
        sidebar.append(spacer)

        main_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        root.append(main_panel)

        log_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        log_header.add_css_class("log-header")
        log_title = Gtk.Label(label="ACTIVITY LOG")
        log_title.add_css_class("log-title")
        log_header.append(log_title)
        main_panel.append(log_header)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_hexpand(True)
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        main_panel.append(scroll)

        self._text_view = Gtk.TextView()
        self._text_view.set_editable(False)
        self._text_view.set_cursor_visible(False)
        self._text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._text_view.set_left_margin(16)
        self._text_view.set_right_margin(16)
        self._text_view.set_top_margin(12)
        self._text_view.set_bottom_margin(12)
        scroll.set_child(self._text_view)

        self._buf = self._text_view.get_buffer()
        self._scroll_win = scroll
        self._setup_tags()
        self._append_log("SERVER", "GUI Ready. Press START SERVER.")

    def _setup_tags(self):
        tag_table = self._buf.get_tag_table()

        def make_tag(name, **props):
            tag = Gtk.TextTag.new(name)
            for k, v in props.items():
                tag.set_property(k.replace("_", "-"), v)
            tag_table.add(tag)

        make_tag("timestamp", foreground="#6e7681", family="monospace", size_points=10)
        make_tag("badge_SERVER", foreground="#58a6ff", weight=Pango.Weight.BOLD)
        make_tag("badge_REQUEST", foreground="#3fb950", weight=Pango.Weight.BOLD)
        make_tag("badge_RESPONSE", foreground="#79c0ff", weight=Pango.Weight.BOLD)
        make_tag("badge_INFO", foreground="#e3b341", weight=Pango.Weight.BOLD)
        make_tag("badge_ERROR", foreground="#f85149", weight=Pango.Weight.BOLD)
        make_tag("msg_SERVER", foreground="#cdd9e5")
        make_tag("msg_REQUEST", foreground="#aff5b4")
        make_tag("msg_RESPONSE", foreground="#cae8ff")
        make_tag("msg_INFO", foreground="#ffd8b5")
        make_tag("msg_ERROR", foreground="#ffa198")
        make_tag("divider", foreground="#21262d")

    def _append_log(self, level: str, message: str):
        ts  = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        buf = self._buf
        end = buf.get_end_iter()

        buf.insert_with_tags_by_name(end, f"{ts}  ", "timestamp")

        badge_map = {
            "SERVER": "[ SRV ]",
            "REQUEST": "[ REQ ]",
            "RESPONSE": "[ RES ]",
            "INFO": "[ INF ]",
            "ERROR": "[ ERR ]",
        }
        badge_text = badge_map.get(level, f"[{level[:3]}]")
        buf.insert_with_tags_by_name(end, f"{badge_text} ", f"badge_{level}")

        plain_msg = message.replace("<b>", "").replace("</b>", "")
        buf.insert_with_tags_by_name(end, plain_msg, f"msg_{level}")
        buf.insert(end, "\n")

        GLib.idle_add(self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        adj = self._scroll_win.get_vadjustment()
        adj.set_value(adj.get_upper() - adj.get_page_size())
        return False

    def _on_log(self, level: str, message: str):
        self._append_log(level, message)
        if level == "REQUEST":
            self._req_count += 1
            self._lbl_req.set_text(str(self._req_count))
        elif level == "ERROR":
            self._err_count += 1
            self._lbl_err.set_markup(f'<span foreground="#f85149">{self._err_count}</span>')
        return False

    def _on_browser_changed(self, dropdown, _param):
        idx     = dropdown.get_selected()
        browser = BROWSERS[idx] if idx < len(BROWSERS) else ""
        set_cookies_browser(browser)
        emit_log("SERVER", f"🍪 Cookies browser: {browser or 'disabled'}")
        save_config(
            self._port_entry.get_text().strip(),
            self._proxy_entry.get_text().strip(),
            self._proxy_switch.get_active(),
            browser,
        )


    def _on_proxy_toggle(self, switch, _param):
        enabled = switch.get_active()
        if enabled:
            proxy = self._proxy_entry.get_text().strip()
            if not proxy:
                switch.set_active(False)
                self._append_log("ERROR", "fil proxy before switch!")
                return
            self._proxy_status_lbl.set_text("ON")
            self._proxy_status_lbl.remove_css_class("toggle-off")
            self._proxy_status_lbl.add_css_class("toggle-on")
            emit_log("SERVER", f"🔒 Proxy enabled: {proxy}")
        else:
            self._proxy_status_lbl.set_text("OFF")
            self._proxy_status_lbl.remove_css_class("toggle-on")
            self._proxy_status_lbl.add_css_class("toggle-off")
            emit_log("SERVER", "🌐 Proxy disabled")

        save_config(
            self._port_entry.get_text().strip(),
            self._proxy_entry.get_text().strip(),
            enabled,
            BROWSERS[self._browser_dropdown.get_selected()],
        )


    def _on_start(self, _btn):
        try:
            port = int(self._port_entry.get_text().strip())
        except ValueError:
            self._append_log("ERROR", "Port Number only!")
            return

        proxy_text    = self._proxy_entry.get_text().strip()
        proxy_enabled = self._proxy_switch.get_active()
        browser = BROWSERS[self._browser_dropdown.get_selected()]
        set_proxy(proxy_text if proxy_enabled else "")
        set_cookies_browser(browser)
        save_config(str(port), proxy_text, proxy_enabled, browser)


        from server import get_proxy
        if get_proxy():
            emit_log("SERVER", f"🔒 Proxy active: {get_proxy()}")
        else:
            emit_log("SERVER", "🌐 Direct connection (proxy off)")

        self._server_mgr.start(port)
        if self._server_mgr.running:
            self._btn_start.set_sensitive(False)
            self._btn_stop.set_sensitive(True)
            self._port_entry.set_sensitive(False)
            self._proxy_entry.set_sensitive(False)
            self._status_dot.set_text("● ONLINE")
            self._status_dot.remove_css_class("status-dot-off")
            self._status_dot.add_css_class("status-dot-on")
            self.set_hide_on_close(True)
            emit_log("SERVER", "✅ Running in Background")

    def _on_stop(self, _btn):
        self._server_mgr.stop()
        set_proxy("")
        self._btn_start.set_sensitive(True)
        self._btn_stop.set_sensitive(False)
        self._port_entry.set_sensitive(True)
        self._proxy_entry.set_sensitive(True)
        self._status_dot.set_text("● OFFLINE")
        self._status_dot.remove_css_class("status-dot-on")
        self._status_dot.add_css_class("status-dot-off")
        self.set_hide_on_close(False)
        emit_log("SERVER", "✅ Stopped")

    def _on_clear(self, _btn):
        self._buf.set_text("")
        self._req_count = 0
        self._err_count = 0
        self._lbl_req.set_text("0")
        self._lbl_err.set_markup('<span foreground="#f85149">0</span>')
        self._append_log("SERVER", "Log clered.")
