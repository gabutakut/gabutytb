#!/usr/bin/env python3

import gi
import math
import random

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib, GObject

import cairo

PLATFORMS = [
    ("YT",  1.00, 0.00, 0.00),
    ("TW",  0.58, 0.18, 0.98),
    ("TK",  0.01, 0.01, 0.01),
    ("SC",  1.00, 0.33, 0.00),
    ("VM",  0.17, 0.52, 0.96),
    ("NF",  0.90, 0.00, 0.00),
    ("FB",  0.23, 0.36, 0.60),
    ("IG",  0.86, 0.20, 0.45),
    ("DM",  0.10, 0.10, 0.10),
    ("TW2", 0.11, 0.63, 0.95),
    ("NI",  0.61, 0.72, 0.88),
    ("RC",  1.00, 0.20, 0.20),
]

class SplashScreen(Gtk.Window, GObject.GObject):

    __gtype_name__ = "SplashScreen"
    __gsignals__ = {"preparing": ( GObject.SignalFlags.RUN_FIRST, None, ()),}

    def __init__(self, app):
        super().__init__(application=app, decorated=False, resizable=False)
        self.set_default_size(520, 320)

        self._tick = 0.0
        self._ring_angle = 0.0
        self._pulse = 1.0
        self._pulse_up = True
        self._running = True
        self._fraction = 0.0
        self._status = "Initializing…"

        self._particles = [self._make_particle(rand=True) for _ in range(65)]

        self._streams = [ {
                "offset": random.uniform(0, 520),
                "speed":  random.uniform(1.2, 3.8),
                "alpha":  random.uniform(0.06, 0.22),
                "width":  random.uniform(25, 80),
                "y":      random.uniform(0.45, 0.90),
            }
            for _ in range(14)
        ]

        self._orbit_items = [p for p in PLATFORMS if p[0] != "YT"]
        random.shuffle(self._orbit_items)
        self._orbit_items = self._orbit_items[:8]

        self._area = Gtk.DrawingArea()
        self._area.set_draw_func(self._draw)
        self.set_child(self._area)

        GLib.timeout_add(14, self._on_tick)
        self.set_opacity(0.0)
        self._fade_in()

    def set_status(self, text: str, fraction: float = None):
        self._status = text
        if fraction is not None:
            self._fraction = max(0.0, min(1.0, fraction))
        GLib.idle_add(self._area.queue_draw)

    def fade_out(self, on_done=None):
        def _tick():
            op = self.get_opacity() - 0.05
            if op <= 0.0:
                self._running = False
                self.close()
                if on_done:
                    on_done()
                return False
            self.set_opacity(op)
            return True
        GLib.timeout_add(10, _tick)

    def _fade_in(self):
        def _tick():
            op = self.get_opacity() + 0.05
            if op >= 1.0:
                self.emit("preparing")
                self.set_opacity(1.0)
                return False
            self.set_opacity(op)
            return True
        GLib.timeout_add(10, _tick)

    def _on_tick(self):
        if not self._running:
            return False

        self._tick += 0.032
        self._ring_angle += 0.022

        if self._pulse_up:
            self._pulse += 0.0025
            if self._pulse >= 1.055:
                self._pulse_up = False
        else:
            self._pulse -= 0.0025
            if self._pulse <= 0.945:
                self._pulse_up = True

        new_p = []
        for p in self._particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] += 1
            p["alpha"] = 1.0 - p["life"] / p["max_life"]
            new_p.append(self._make_particle(rand=False) if p["life"] >= p["max_life"] else p)
        self._particles = new_p

        for s in self._streams:
            s["offset"] += s["speed"]
            if s["offset"] > 620:
                s["offset"] = -s["width"]

        self._area.queue_draw()
        return True

    def _make_particle(self, rand=False):
        cx, cy = 260.0, 120.0
        if rand:
            x = random.uniform(0, 520)
            y = random.uniform(0, 220)
        else:
            edge = random.randint(0, 2)
            if edge == 0:
                x, y = random.uniform(0, 520), -8
            elif edge == 1:
                x, y = -8, random.uniform(0, cy)
            else:
                x, y = 528, random.uniform(0, cy)

        dx = cx - x + random.uniform(-30, 30)
        dy = cy - y + random.uniform(-15, 15)
        d  = math.sqrt(dx*dx + dy*dy) or 1
        sp = random.uniform(0.3, 1.3)
        return {
            "x": x, "y": y,
            "vx": dx/d * sp, "vy": dy/d * sp,
            "alpha": 1.0,
            "size": random.uniform(1.5, 3.8),
            "max_life": random.uniform(55, 130),
            "life": 0,
            "kind": random.randint(0, 2),
        }

    def _draw(self, area, cr, w, h):
        cx, cy = w / 2.0, h / 2.0 - 28
        self._bg(cr, w, h, cx, cy)
        self._streams_draw(cr, w, h)
        self._halo(cr, cx, cy)
        self._particles_draw(cr)
        self._deco_ring(cr, cx, cy)
        self._orbit_icons(cr, cx, cy)
        self._youtube_center(cr, cx, cy)
        self._appname(cr, cx, cy)
        self._status_bar(cr, w, h)

    def _bg(self, cr, w, h, cx, cy):
        pat = cairo.RadialGradient(cx, cy, 0, cx, cy, w * 0.85)
        pat.add_color_stop_rgb(0.0, 0.07, 0.04, 0.12)
        pat.add_color_stop_rgb(0.5, 0.03, 0.02, 0.06)
        pat.add_color_stop_rgb(1.0, 0.01, 0.01, 0.02)
        cr.set_source(pat)
        cr.rectangle(0, 0, w, h)
        cr.fill()

    def _streams_draw(self, cr, w, h):
        for i, s in enumerate(self._streams):
            y = h * s["y"]
            r, g2, b = (0.63, 0.0, 0.90) if i % 2 == 0 else (1.0, 0.0, 0.03)
            pat = cairo.LinearGradient(s["offset"], 0, s["offset"] + s["width"], 0)
            pat.add_color_stop_rgba(0.0, r, g2, b, 0.0)
            pat.add_color_stop_rgba(0.4, r, g2, b, s["alpha"])
            pat.add_color_stop_rgba(0.7, r, g2, b, s["alpha"] * 0.5)
            pat.add_color_stop_rgba(1.0, r, g2, b, 0.0)
            cr.set_source(pat)
            cr.rectangle(s["offset"], y, s["width"], 2.0)
            cr.fill()

    def _halo(self, cr, cx, cy):
        pulse = 52 + math.sin(self._tick * 1.3) * 7
        halo = cairo.RadialGradient(cx, cy, 0, cx, cy, pulse * 2.4)
        a = 0.14 * self._pulse
        halo.add_color_stop_rgba(0.00, 0.63, 0.0, 0.9, a * 1.4)
        halo.add_color_stop_rgba(0.35, 0.63, 0.0, 0.9, a * 0.6)
        halo.add_color_stop_rgba(0.60, 1.0, 0.1, 0.0, a * 0.3)
        halo.add_color_stop_rgba(1.00, 0.0, 0.0, 0.0, 0.0)
        cr.set_source(halo)
        cr.arc(cx, cy, pulse * 2.4, 0, 2 * math.pi)
        cr.fill()

    def _particles_draw(self, cr):
        for i, p in enumerate(self._particles):
            if p["alpha"] <= 0:
                continue
            a = p["alpha"] * 0.80
            k = p["kind"]
            if k == 0:
                pat = cairo.RadialGradient(p["x"], p["y"], 0, p["x"], p["y"], p["size"] * 2.2)
                c = [(0.88, 0.77, 0.14), (0.63, 0.0, 0.9), (1.0, 0.14, 0.03)][i % 3]
                pat.add_color_stop_rgba(0, *c, a)
                pat.add_color_stop_rgba(1, *c, 0)
                cr.set_source(pat)
                cr.arc(p["x"], p["y"], p["size"] * 2.2, 0, 2 * math.pi)
                cr.fill()
            elif k == 1:
                cr.set_source_rgba(0.88, 0.77, 0.14, a * 0.65)
                cr.set_line_width(1.0)
                cr.move_to(p["x"], p["y"])
                cr.line_to(p["x"] - p["vx"] * 5, p["y"] - p["vy"] * 5)
                cr.stroke()
            else:
                cr.set_source_rgba(0.63, 0.0, 0.9, a * 0.5)
                cr.rectangle(p["x"] - p["size"]/2, p["y"] - p["size"]/2, p["size"], p["size"])
                cr.fill()

    def _deco_ring(self, cr, cx, cy):
        R = 58.0 * self._pulse
        cr.save()
        cr.translate(cx, cy)

        cr.rotate(self._ring_angle)
        cr.set_line_width(2.0)
        for i in range(12):
            a1 = i * 2 * math.pi / 12
            a2 = a1 + math.pi / 12 * 0.55
            br = 0.4 + 0.6 * math.sin(self._tick * 2.5 + i * 0.9)
            colors = [(0.88, 0.77, 0.14), (0.63, 0.0, 0.9), (1.0, 0.14, 0.03)]
            cr.set_source_rgba(*colors[i % 3], br * 0.75)
            cr.arc(0, 0, R, a1, a2)
            cr.stroke()

        cr.rotate(-self._ring_angle * 1.7)
        cr.set_line_width(1.2)
        for i in range(8):
            a1 = i * 2 * math.pi / 8
            a2 = a1 + math.pi / 8 * 0.4
            cr.set_source_rgba(0.88, 0.77, 0.14, 0.35)
            cr.arc(0, 0, R - 8, a1, a2)
            cr.stroke()

        cr.restore()

    def _orbit_icons(self, cr, cx, cy):
        n = len(self._orbit_items)
        inner_r = 72.0
        outer_r = 110.0

        for i, (label, r, g2, b) in enumerate(self._orbit_items):
            if i < n // 2:
                orbit_r = inner_r
                speed   = 0.38
                scale_y = 0.52
            else:
                orbit_r = outer_r
                speed   = 0.26
                scale_y = 0.45

            phase = self._tick * speed + i * (2 * math.pi / n)
            px = cx + math.cos(phase) * orbit_r
            py = cy + math.sin(phase) * orbit_r * scale_y

            depth = (math.sin(phase) + 1) / 2
            alpha = 0.45 + 0.50 * depth
            icon_r = 11 + 4 * depth

            self._mini_badge(cr, px, py, label, r, g2, b, alpha, icon_r)

            cr.save()
            cr.translate(cx, cy)
            cr.scale(1.0, scale_y)
            cr.set_source_rgba(r, g2, b, 0.07 + 0.04 * depth)
            cr.set_line_width(0.8)
            cr.arc(0, 0, orbit_r, 0, 2 * math.pi)
            cr.stroke()
            cr.restore()

    def _mini_badge(self, cr, x, y, label, r, g2, b, alpha, icon_r=13):
        cr.save()
        shadow = cairo.RadialGradient(x + 1, y + 2, 0, x + 1, y + 2, icon_r * 1.6)
        shadow.add_color_stop_rgba(0.0, 0, 0, 0, alpha * 0.4)
        shadow.add_color_stop_rgba(1.0, 0, 0, 0, 0.0)
        cr.set_source(shadow)
        cr.arc(x + 1, y + 2, icon_r * 1.6, 0, 2 * math.pi)
        cr.fill()

        bg = cairo.RadialGradient(x - icon_r * 0.3, y - icon_r * 0.3, 0, x, y, icon_r)
        bg.add_color_stop_rgba(0.0, min(r + 0.30, 1), min(g2 + 0.20, 1), min(b + 0.20, 1), alpha)
        bg.add_color_stop_rgba(1.0, r * 0.7, g2 * 0.7, b * 0.7, alpha)
        cr.set_source(bg)
        cr.arc(x, y, icon_r, 0, 2 * math.pi)
        cr.fill()

        cr.set_source_rgba(1.0, 1.0, 1.0, alpha * 0.35)
        cr.set_line_width(1.2)
        cr.arc(x, y, icon_r, 0, 2 * math.pi)
        cr.stroke()

        sh_angle = self._ring_angle * 1.5
        cr.set_source_rgba(1, 1, 1, alpha * 0.22)
        cr.set_line_width(1.5)
        cr.arc(x, y, icon_r * 0.7, sh_angle, sh_angle + math.pi * 0.55)
        cr.stroke()

        cr.set_source_rgba(1.0, 1.0, 1.0, alpha * 0.92)
        cr.select_font_face("Monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        font_size = max(5.5, icon_r * 0.55)
        cr.set_font_size(font_size)
        ext = cr.text_extents(label)
        cr.move_to(x - ext.width / 2 - ext.x_bearing, y - ext.height / 2 - ext.y_bearing)
        cr.show_text(label)
        cr.restore()

    def _youtube_center(self, cr, cx, cy):
        sc = self._pulse
        w2 = 40 * sc
        h2 = 28 * sc
        r = 9 * sc

        glow = cairo.RadialGradient(cx, cy, 0, cx, cy, 60)
        ga = 0.18 + 0.12 * math.sin(self._tick * 2.5)
        glow.add_color_stop_rgba(0.0, 1.0, 0.05, 0.05, ga * 2.0)
        glow.add_color_stop_rgba(0.6, 1.0, 0.0,  0.0,  ga * 0.3)
        glow.add_color_stop_rgba(1.0, 0.0, 0.0,  0.0,  0.0)
        cr.set_source(glow)
        cr.arc(cx, cy, 60, 0, 2 * math.pi)
        cr.fill()

        self._rrect(cr, cx - w2, cy - h2, w2*2, h2*2, r)
        grad = cairo.LinearGradient(cx - w2, cy - h2, cx - w2, cy + h2)
        grad.add_color_stop_rgba(0.0, 1.00, 0.12, 0.08, 0.97)
        grad.add_color_stop_rgba(1.0, 0.72, 0.0,  0.0,  0.97)
        cr.set_source(grad)
        cr.fill()

        cr.save()
        cr.rectangle(cx - w2 + 2, cy - h2 + 2, w2*2 - 4, h2 - 2)
        cr.clip()
        shine = cairo.LinearGradient(cx, cy - h2, cx, cy)
        shine.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.20)
        shine.add_color_stop_rgba(1.0, 1.0, 1.0, 1.0, 0.0)
        cr.set_source(shine)
        self._rrect(cr, cx - w2, cy - h2, w2*2, h2*2, r)
        cr.fill()
        cr.restore()

        sh = self._ring_angle * 2.8
        cr.set_source_rgba(1.0, 0.5, 0.5, 0.28)
        cr.set_line_width(1.8)
        cr.arc(cx, cy, (w2 + h2) / 2 * 1.05, sh, sh + math.pi * 0.4)
        cr.stroke()

        pt = 20 * sc
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.97)
        cr.move_to(cx - pt * 0.48, cy - pt * 0.72)
        cr.line_to(cx + pt * 0.96, cy)
        cr.line_to(cx - pt * 0.48, cy + pt * 0.72)
        cr.close_path()
        cr.fill()

        cr.select_font_face("Monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(8.5)
        tag = "yt-dlp"
        ext = cr.text_extents(tag)
        tx = cx - ext.width / 2 - ext.x_bearing
        ty = cy + h2 + 14

        cr.set_source_rgba(0.63, 0.0, 0.9, 0.30)
        cr.move_to(tx + 1, ty + 1)
        cr.show_text(tag)

        tg = cairo.LinearGradient(tx, 0, tx + ext.width, 0)
        tg.add_color_stop_rgb(0.0, 0.88, 0.77, 0.14)
        tg.add_color_stop_rgb(0.5, 0.75, 0.92, 1.00)
        tg.add_color_stop_rgb(1.0, 1.00, 0.14, 0.03)
        cr.set_source(tg)
        cr.move_to(tx, ty)
        cr.show_text(tag)

    def _appname(self, cr, cx, cy):
        cr.save()

        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(17)
        title = "Gabut YTB"
        ext = cr.text_extents(title)
        tx = cx - ext.width / 2 - ext.x_bearing
        ty = cy + 80

        cr.set_source_rgba(0, 0, 0, 0.55)
        cr.move_to(tx + 1, ty + 2)
        cr.show_text(title)

        cr.set_source_rgba(0.88, 0.77, 0.14, 0.28)
        cr.move_to(tx, ty)
        cr.show_text(title)

        tg = cairo.LinearGradient(tx, 0, tx + ext.width, 0)
        tg.add_color_stop_rgb(0.0, 0.88, 0.77, 0.14)
        tg.add_color_stop_rgb(0.5, 0.96, 0.94, 1.00)
        tg.add_color_stop_rgb(1.0, 1.00, 0.14, 0.03)
        cr.set_source(tg)
        cr.move_to(tx, ty)
        cr.show_text(title)

        cr.set_font_size(8)
        sub = "Video Downloader yt-dlp JSON-RPC Server"
        ext2 = cr.text_extents(sub)
        cr.set_source_rgba(0.55, 0.65, 0.82, 0.72)
        cr.move_to(cx - ext2.width / 2 - ext2.x_bearing, ty + 15)
        cr.show_text(sub)

        cr.restore()

    def _status_bar(self, cr, w, h):
        margin = 20.0
        bar_h = 6.0
        bar_y = h - margin - bar_h
        bar_w = w - margin * 2
        lbl_y = bar_y - 16.0

        cr.save()
        cr.select_font_face("Monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(8)
        text = self._status
        ext = cr.text_extents(text)
        cr.set_source_rgba(0, 0, 0, 0.5)
        cr.move_to(margin + 1, lbl_y + 1)
        cr.show_text(text)
        tg = cairo.LinearGradient(margin, 0, margin + min(ext.width, bar_w), 0)
        tg.add_color_stop_rgb(0.0, 0.88, 0.77, 0.14)
        tg.add_color_stop_rgb(0.5, 0.78, 0.88, 1.00)
        tg.add_color_stop_rgb(1.0, 1.00, 0.14, 0.03)
        cr.set_source(tg)
        cr.move_to(margin, lbl_y)
        cr.show_text(text)
        cr.restore()

        r = bar_h / 2.0
        self._rrect(cr, margin, bar_y, bar_w, bar_h, r)
        cr.set_source_rgba(0.05, 0.10, 0.20, 0.80)
        cr.fill()
        self._rrect(cr, margin, bar_y, bar_w, bar_h, r)
        cr.set_source_rgba(0.4, 0.2, 0.6, 0.40)
        cr.set_line_width(0.8)
        cr.stroke()

        if self._fraction > 0.0:
            fill_w = bar_w * self._fraction
            cr.save()
            cr.rectangle(margin, bar_y, fill_w, bar_h)
            cr.clip()
            self._rrect(cr, margin, bar_y, bar_w, bar_h, r)
            pg = cairo.LinearGradient(margin, 0, margin + bar_w, 0)
            pg.add_color_stop_rgb(0.0, 0.63, 0.0,  0.90)
            pg.add_color_stop_rgb(0.4, 0.88, 0.50, 0.14)
            pg.add_color_stop_rgb(1.0, 1.0,  0.14, 0.03)
            cr.set_source(pg)
            cr.fill()
            cr.set_source_rgba(1, 1, 1, 0.18)
            self._rrect(cr, margin, bar_y, fill_w, bar_h / 2, r)
            cr.fill()
            cr.restore()

            if self._fraction < 1.0:
                ex = margin + bar_w * self._fraction
                ey = bar_y + bar_h / 2
                ga = 0.55 + 0.45 * math.sin(self._tick * 6.0)
                eg = cairo.RadialGradient(ex, ey, 0, ex, ey, 9)
                eg.add_color_stop_rgba(0.0, 1.0, 0.9, 0.4, ga * 0.95)
                eg.add_color_stop_rgba(1.0, 1.0, 0.9, 0.4, 0.0)
                cr.set_source(eg)
                cr.arc(ex, ey, 9, 0, 2 * math.pi)
                cr.fill()

    def _rrect(self, cr, x, y, w, h, r):
        cr.new_path()
        cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
        cr.arc(x + w - r, y + r,     r, 3 * math.pi / 2, 0)
        cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
        cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
        cr.close_path()
