#!/usr/bin/env python3

import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

from gi.repository import GLib

try:
    import yt_dlp
    HAS_YTDLP = True
    from yt_dlp.utils import std_headers
except ImportError:
    HAS_YTDLP = False

_log_callback = None
_proxy_value   = ""


def set_log_callback(fn):
    global _log_callback
    _log_callback = fn


def emit_log(level: str, message: str):
    if _log_callback:
        GLib.idle_add(_log_callback, level, message)


def get_proxy() -> str:
    return _proxy_value


def set_proxy(value: str):
    global _proxy_value
    _proxy_value = value

 
def get_cookies_browser() -> str:
    return _cookies_browser
 
 
def set_cookies_browser(value: str):
    global _cookies_browser
    _cookies_browser = value
 
 

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    address_family = socket.AF_INET
    daemon_threads = True


class RPCHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            req = json.loads(body)
        except json.JSONDecodeError:
            self.send_rpc_error(-32700, "Parse error")
            return

        method = req.get("method")
        params = req.get("params", {})
        request_id = req.get("id")

        emit_log("REQUEST", f"Method: {method} | Params: {json.dumps(params)[:100]}...")

        response_data = {"jsonrpc": "2.0", "id": request_id}

        if method == "info":
            self._handle_info(params, response_data)
        elif method == "ping":
            self._handle_ping(params, response_data)
        elif method == "headers":
            self._handle_get_headers(params, response_data)
        else:
            response_data["error"] = {"code": -32601, "message": "Method not found"}
            emit_log("ERROR", f"Nothing Method: {method}")

        self._send_rpc_response(response_data)

    def _handle_ping(self, params, response_data):
        url = params.get("url", "").strip()
 
        if not url:
            response_data["result"] = "available"
            emit_log("RESPONSE", "ping: server available ✓")
            return
 
        if not HAS_YTDLP:
            response_data["error"] = {"code": -32000, "message": "yt-dlp not installed"}
            emit_log("ERROR", "ping: yt-dlp not installed")
            return
 
        emit_log("INFO", f"ping check: {url[:60]}")
 
        try:
            from yt_dlp.extractor import gen_extractors
            matched_ie = None
            for ie in gen_extractors():
                try:
                    if ie.suitable(url):
                        if ie.IE_NAME.lower() == "generic":
                            continue
                        matched_ie = ie.IE_NAME
                        break
                except Exception:
                    continue
 
            if matched_ie:
                response_data["result"] = "available"
                emit_log("RESPONSE", f"ping OK ✓ | extractor={matched_ie}")
            else:
                response_data["error"] = {
                    "code":    -32001,
                    "message": "URL not supported by yt-dlp",
                }
                emit_log("ERROR", f"ping: no extractor matched → {url[:60]}")
 
        except Exception as e:
            response_data["error"] = {"code": -32000, "message": str(e)[:200]}
            emit_log("ERROR", f"ping: {str(e)[:80]}")

    def _handle_get_headers(self, params, response_data):
        url = params.get("url")
        if not url:
            response_data["error"] = {"code": -32602, "message": "Missing URL"}
            return

        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "no_warnings": True,
            "noplaylist": True,
        }
        proxy = get_proxy()
        if proxy:
            ydl_opts["proxy"] = proxy

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                cookies_list = []
                try:
                    for cookie in ydl.cookiejar:
                        cookies_list.append({
                            "name": cookie.name,
                            "value": cookie.value,
                            "domain": cookie.domain,
                            "path": cookie.path,
                            "secure": bool(cookie.secure),
                        })
                except Exception:
                    pass

                cookie_header = "; ".join(f"{c['name']}={c['value']}" for c in cookies_list)
                http_headers = dict(info.get("http_headers", {}))

                user_agent = (
                    http_headers.get("User-Agent")
                    or ydl.params.get("http_headers", {}).get("User-Agent")
                    or std_headers.get("User-Agent", "")
                )

                if not http_headers.get("Referer"):
                    for f in info.get("formats", []):
                        ref = f.get("http_headers", {}).get("Referer", "")
                        if ref:
                            http_headers["Referer"] = ref
                            break

                referer = http_headers.get("Referer", "")
                origin  = http_headers.get("Origin",  "")

                response_data["result"] = {
                    "user_agent": user_agent,
                    "referer": referer,
                    "origin": origin,
                    "cookie_header": cookie_header,
                    "cookies": cookies_list,
                    "http_headers": http_headers,
                }
                emit_log("INFO", f"📦 Headers | UA: {user_agent[:40]} | {len(cookies_list)} cookies")

        except Exception as e:
            err_msg = str(e)
            response_data["error"] = {"code": -32000, "message": err_msg}
            emit_log("ERROR", f"headers error: {err_msg[:100]}")

    def _handle_info(self, params, response_data):
        url = params.get("url")
        if not url:
            response_data["error"] = {"code": -32602, "message": "Missing URL"}
            emit_log("ERROR", "Parameter nothing URL")
            return

        emit_log("INFO", f"Fetch info: {url[:60]}")

        if not HAS_YTDLP:
            response_data["error"] = {"code": -32000, "message": "yt-dlp not installed"}
            emit_log("ERROR", "yt-dlp no installed in system")
            return

        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "no_warnings": True,
            "extract_flat": False,
            "noplaylist": True,
        }

        proxy = get_proxy()
        if proxy:
            ydl_opts["proxy"] = proxy
            emit_log("INFO", f"Menggunakan proxy: {proxy}")

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                user_agent = (
                    info.get("http_headers", {}).get("User-Agent")
                    or ydl.params.get("http_headers", {}).get("User-Agent")
                    or std_headers.get("User-Agent", "")
                )

                cookies_dict  = {}
                cookie_header = ""
                try:
                    cookies_list = []
                    for cookie in ydl.cookiejar:
                        cookies_dict[cookie.name] = cookie.value
                        cookies_list.append(f"{cookie.name}={cookie.value}")
                    cookie_header = "; ".join(cookies_list)
                except Exception:
                    pass

                referer = ""
                for f in info.get("formats", []):
                    ref = f.get("http_headers", {}).get("Referer", "")
                    if ref:
                        referer = ref
                        break

                formats = []
                for f in info.get("formats", []):
                    fmt_headers = dict(f.get("http_headers", {}))
                    formats.append({
                        "format_id": f.get("format_id"),
                        "ext": f.get("ext"),
                        "resolution": f.get("resolution") or f.get("format_note") or "audio",
                        "filesize": f.get("filesize") or f.get("filesize_approx") or 0,
                        "url": f.get("url"),
                        "vcodec": f.get("vcodec") or "none",
                        "acodec": f.get("acodec") or "none",
                        "http_headers" : fmt_headers,
                    })

                response_data["result"] = {
                    "title": info.get("title"),
                    "duration": info.get("duration"),
                    "thumbnail": info.get("thumbnail"),
                    "uploader": info.get("uploader"),
                    "user_agent": user_agent,
                    "referer": referer,
                    "cookie_header" : cookie_header,
                    "cookies": cookies_dict,
                    "http_headers" : dict(info.get("http_headers", {})),
                    "formats": formats,
                }
                emit_log("RESPONSE", f"✓ {info.get('title','')[:40]} | {len(formats)} fmt | UA: {user_agent[:30]}")

        except Exception as e:
            err_msg = str(e)
            response_data["error"] = {"code": -32000, "message": err_msg}
            emit_log("ERROR", f"yt-dlp Error: {err_msg[:100]}")

    def _send_rpc_response(self, response_dict):
        try:
            data = json.dumps(response_dict).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type",                "application/json")
            self.send_header("Content-Length",              str(len(data)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            emit_log("ERROR", f"Failed sending respond: {e}")

    def send_rpc_error(self, code, message):
        self._send_rpc_response({
            "jsonrpc": "2.0",
            "error": {"code": code, "message": message},
            "id": None,
        })

class ServerManager:
    def __init__(self):
        self._server = None
        self._thread = None
        self.running  = False

    def start(self, port: int):
        if self.running:
            return
        try:
            self._server = ThreadedHTTPServer(("0.0.0.0", port), RPCHandler)
            self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
            self._thread.start()
            self.running = True
            emit_log("SERVER", f"✅ Server actived on port <b>{port}</b>")
        except Exception as e:
            emit_log("ERROR", f"Failed Start server: {e}")

    def stop(self):
        if not self.running:
            return
        self._server.shutdown()
        self._server.server_close()
        self.running = False
        emit_log("SERVER", "🛑 Server Stopped")
