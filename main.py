import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import asyncio
import json
import os
import sys
import time
import logging
import traceback
from datetime import datetime

CONFIG_FILE = "bot_config.json"

discord  = None
commands = None
psutil   = None
HAS_DISCORD = False
HAS_PSUTIL  = False

def _try_import_discord():
    global discord, commands, HAS_DISCORD
    try:
        import discord as _d
        from discord.ext import commands as _c
        discord = _d; commands = _c; HAS_DISCORD = True
        return True, ""
    except ImportError as e:
        return False, str(e)

def _try_import_psutil():
    global psutil, HAS_PSUTIL
    try:
        import psutil as _p
        psutil = _p; HAS_PSUTIL = True
        return True, ""
    except ImportError as e:
        return False, str(e)

C = {
    "bg":        "#2b2d31",
    "sidebar":   "#1e1f22",
    "surface":   "#313338",
    "surface2":  "#383a40",
    "input":     "#3b3d44",
    "accent":    "#5865f2",
    "accent_h":  "#4752c4",
    "green":     "#23a55a",
    "yellow":    "#f0b232",
    "red":       "#f23f43",
    "text":      "#dbdee1",
    "muted":     "#949ba4",
    "white":     "#ffffff",
    "online":    "#23a55a",
    "idle":      "#f0b232",
    "dnd":       "#f23f43",
    "offline":   "#80848e",
    "border":    "#1e1f22",
    "hover":     "#35373c",
    "tag_bg":    "#4e5058",
}

from i18n import TRANSLATIONS, t, set_lang


def load_config() -> dict:
    defaults = {
        "token": "", "prefix": "!", "bot_name": "MyBot",
        "status": "online", "activity": "", "log_level": "INFO", "lang": "en",
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                defaults.update(json.load(f))
        except Exception:
            pass
    return defaults

def save_config(cfg: dict):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

def config_exists() -> bool:
    if not os.path.exists(CONFIG_FILE):
        return False
    try:
        with open(CONFIG_FILE) as f:
            d = json.load(f)
        return bool(d.get("token", "").strip()) and bool(d.get("bot_name", "").strip())
    except Exception:
        return False


class TextWidgetHandler(logging.Handler):
    def __init__(self, widget):
        super().__init__()
        self.widget = widget

    def emit(self, record):
        msg   = self.format(record)
        level = record.levelname
        clr   = {"DEBUG": C["muted"], "INFO": C["text"],
                  "WARNING": C["yellow"], "ERROR": C["red"], "CRITICAL": C["red"]}
        color = clr.get(level, C["text"])

        def _ins():
            try:
                self.widget.configure(state="normal")
                ts = datetime.now().strftime("%H:%M:%S")
                self.widget.insert("end", f"[{ts}] ", "ts")
                self.widget.insert("end", f"[{level}] ", level)
                self.widget.insert("end", msg + "\n", "normal")
                self.widget.tag_config("ts",     foreground=C["muted"])
                self.widget.tag_config(level,    foreground=color)
                self.widget.tag_config("normal", foreground=C["text"])
                self.widget.see("end")
                self.widget.configure(state="disabled")
            except Exception:
                pass
        try:
            self.widget.after(0, _ins)
        except Exception:
            pass

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
for _n in ("discord", "asyncio", "yt_dlp", "urllib3"):
    logging.getLogger(_n).setLevel(logging.WARNING)


def show_error_popup(parent, title: str, tb: str):
    try:
        win = tk.Toplevel(parent)
        win.title(f"Error — {title}")
        win.configure(bg=C["sidebar"])
        win.geometry("740x460")
        win.resizable(True, True)
        win.grab_set()

        hdr = tk.Frame(win, bg=C["red"])
        hdr.pack(fill="x")
        tk.Label(hdr, text=f"  ⚠  {title}", font=("Segoe UI", 11, "bold"),
                 bg=C["red"], fg=C["white"], pady=12).pack(anchor="w")

        box = scrolledtext.ScrolledText(
            win, bg=C["input"], fg="#ff7070",
            font=("Consolas", 9), relief="flat", bd=0, padx=10, pady=10)
        box.pack(fill="both", expand=True, padx=1, pady=1)
        box.insert("1.0", tb)
        box.configure(state="disabled")

        bar = tk.Frame(win, bg=C["surface"], pady=10)
        bar.pack(fill="x")

        def _copy():
            win.clipboard_clear(); win.clipboard_append(tb)
        tk.Button(bar, text=t("err_popup_copy"), bg=C["surface2"], fg=C["text"],
                  relief="flat", bd=0, padx=16, pady=6, font=("Segoe UI", 9),
                  cursor="hand2", command=_copy).pack(side="left", padx=12)
        tk.Button(bar, text=t("err_popup_close"), bg=C["accent"], fg=C["white"],
                  relief="flat", bd=0, padx=16, pady=6, font=("Segoe UI", 9, "bold"),
                  cursor="hand2", command=win.destroy).pack(side="right", padx=12)
    except Exception:
        pass

_dashboard_ref = None

def _global_exc_hook(exc_type, exc_value, exc_tb):
    tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    root_logger.error(tb_str)
    try:
        if _dashboard_ref and _dashboard_ref.winfo_exists():
            _dashboard_ref.after(0, lambda: show_error_popup(_dashboard_ref, "Unexpected Error", tb_str))
    except Exception:
        pass

def _thread_exc_hook(args):
    tb_str = "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))
    root_logger.error(tb_str)
    try:
        if _dashboard_ref and _dashboard_ref.winfo_exists():
            _dashboard_ref.after(0, lambda: show_error_popup(_dashboard_ref, "Thread Error", tb_str))
    except Exception:
        pass

sys.excepthook       = _global_exc_hook
threading.excepthook = _thread_exc_hook


def _styled_button(parent, text, command, variant="default", **kw):
    palettes = {
        "default": (C["surface2"], C["text"]),
        "primary": (C["accent"],   C["white"]),
        "danger":  (C["red"],      C["white"]),
        "success": (C["green"],    C["white"]),
        "ghost":   (C["surface"],  C["muted"]),
    }
    bg, fg = palettes.get(variant, palettes["default"])
    btn = tk.Button(parent, text=text, bg=bg, fg=fg, activebackground=bg,
                    activeforeground=fg, relief="flat", bd=0, cursor="hand2",
                    font=("Segoe UI", 9), command=command,
                    padx=kw.pop("padx", 14), pady=kw.pop("pady", 7), **kw)
    return btn

def _entry(parent, variable, show=None, width=30, font_size=10):
    kw = dict(textvariable=variable, width=width, bg=C["surface2"], fg=C["white"],
              insertbackground=C["white"], relief="flat",
              font=("Segoe UI", font_size), bd=8,
              highlightthickness=1, highlightbackground=C["surface2"],
              highlightcolor=C["accent"])
    if show:
        kw["show"] = show
    return tk.Entry(parent, **kw)

def _label(parent, text, size=9, bold=False, color=None, **kw):
    return tk.Label(parent, text=text,
                    font=("Segoe UI", size, "bold" if bold else "normal"),
                    bg=kw.pop("bg", C["bg"]), fg=color or C["text"], **kw)

def _divider(parent, color=None):
    tk.Frame(parent, bg=color or C["border"], height=1).pack(fill="x")

def _section_label(parent, key):
    tk.Label(parent, text=t(key), font=("Segoe UI", 8, "bold"),
             bg=C["bg"], fg=C["muted"],
             pady=4).pack(anchor="w", padx=24, pady=(18, 4))


class SetupWizard(tk.Toplevel):
    def __init__(self, parent, on_complete):
        super().__init__(parent)
        self.on_complete = on_complete
        self.title(t("setup_title"))
        self.configure(bg=C["sidebar"])
        self.geometry("520x560")
        self.resizable(False, False)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", lambda: None)

        self._v_name   = tk.StringVar(value="MyBot")
        self._v_prefix = tk.StringVar(value="!")
        self._v_token  = tk.StringVar()
        self._v_lang   = tk.StringVar(value="en")

        self._build()
        self._center(parent)

    def _center(self, parent):
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"520x560+{(sw - 520) // 2}+{(sh - 560) // 2}")

    def _build(self):
        # ── Header ──────────────────────────────────────────────────────────
        top = tk.Frame(self, bg=C["accent"])
        top.pack(fill="x", side="top")
        tk.Label(top, text="⚡", font=("Segoe UI", 26),
                 bg=C["accent"], fg=C["white"], pady=14).pack()

        # ── Footer (packed BEFORE body so expand=True doesn't eat it) ───────
        foot = tk.Frame(self, bg=C["surface"], pady=0)
        foot.pack(fill="x", side="bottom")
        tk.Frame(foot, bg=C["border"], height=1).pack(fill="x")
        btn_area = tk.Frame(foot, bg=C["surface"])
        btn_area.pack(fill="x")
        self._err_lbl = tk.Label(btn_area, text="", font=("Segoe UI", 8),
                                  bg=C["surface"], fg=C["red"])
        self._err_lbl.pack(side="left", padx=16, pady=12)
        _styled_button(btn_area, f"{t('setup_continue')}  →", self._finish,
                       variant="primary", padx=28, pady=12
                       ).pack(side="right", padx=16, pady=10)

        # ── Body (fill remaining space) ──────────────────────────────────────
        body = tk.Frame(self, bg=C["sidebar"])
        body.pack(fill="both", expand=True, padx=40, pady=(18, 10))

        tk.Label(body, text=t("setup_title"), font=("Segoe UI", 13, "bold"),
                 bg=C["sidebar"], fg=C["white"]).pack(anchor="w")
        tk.Label(body, text=t("setup_sub"), font=("Segoe UI", 9),
                 bg=C["sidebar"], fg=C["muted"]).pack(anchor="w", pady=(2, 16))

        for label_key, var, show in [
            ("setup_step1", self._v_name,   None),
            ("setup_step2", self._v_prefix, None),
            ("setup_step3", self._v_token,  "•"),
        ]:
            tk.Label(body, text=t(label_key), font=("Segoe UI", 9, "bold"),
                     bg=C["sidebar"], fg=C["muted"]).pack(anchor="w", pady=(8, 2))
            e = _entry(body, var, show=show, width=42, font_size=10)
            e.configure(bg=C["surface2"], highlightbackground=C["accent"],
                        highlightthickness=1)
            e.pack(fill="x")

        tk.Label(body, text=t("setup_token_hint"), font=("Segoe UI", 8),
                 bg=C["sidebar"], fg=C["muted"]).pack(anchor="w", pady=(4, 14))

        tk.Label(body, text=t("set_lang_label"), font=("Segoe UI", 9, "bold"),
                 bg=C["sidebar"], fg=C["muted"]).pack(anchor="w", pady=(0, 4))
        lang_row = tk.Frame(body, bg=C["sidebar"])
        lang_row.pack(anchor="w")
        for code, name in [("en", "English"), ("it", "Italiano"), ("pl", "Polski")]:
            tk.Radiobutton(lang_row, text=name, variable=self._v_lang, value=code,
                           bg=C["sidebar"], fg=C["text"], selectcolor=C["surface2"],
                           activebackground=C["sidebar"], font=("Segoe UI", 9),
                           cursor="hand2").pack(side="left", padx=(0, 16))

    def _finish(self):
        name   = self._v_name.get().strip()
        prefix = self._v_prefix.get().strip()
        token  = self._v_token.get().strip()
        if not all([name, prefix, token]):
            self._err_lbl.configure(text=t("setup_req"))
            return
        set_lang(self._v_lang.get())
        pending_cfg = load_config()
        pending_cfg["bot_name"] = name
        pending_cfg["prefix"]   = prefix
        pending_cfg["token"]    = token
        pending_cfg["lang"]     = self._v_lang.get()
        parent = self.master
        on_complete = self.on_complete
        self.destroy()
        EULAWindow(parent, pending_cfg, on_complete)



EULA_TEXT = """END USER LICENSE AGREEMENT (EULA)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Software:  Discord Bot Dashboard
Author:    Andr3wOnTilt
Version:   1.0.0

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1.  OWNERSHIP

    This software, including its source code, compiled builds, assets, and
    related materials (the "Software"), has been originally created and
    developed by Andr3wOnTilt.

    All intellectual property rights in and to the original version of the
    Software remain the exclusive property of Andr3wOnTilt unless explicitly
    stated otherwise.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

2.  USE OF THE OFFICIAL BUILD

    The official build of the Software, compiled and distributed directly by
    Andr3wOnTilt (the "Official Build"), may be used solely under the following
    conditions:

    ✔  Proper credit to Andr3wOnTilt must always be clearly and visibly
       maintained.

    ✘  The Official Build may NOT be redistributed, repackaged, or re-hosted
       by third parties.

    Failure to comply with these terms immediately voids the right to use the
    Official Build.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

3.  MODIFICATION AND DISTRIBUTION BY THIRD PARTIES

    Third parties are permitted to:

    ✔  Modify the Software.
    ✔  Create derivative works.
    ✔  Build and distribute modified versions of the Software.

    However, the following conditions apply:

    ✔  Proper credit to Andr3wOnTilt as the original creator must be preserved.
    ✔  Any modified version must clearly indicate that it is a modified version
       and not the Official Build.
    ✘  Andr3wOnTilt assumes NO responsibility or liability for any modified,
       rebuilt, redistributed, or derivative versions created by third parties.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

4.  LIABILITY DISCLAIMER

    The Software is provided "AS IS", without warranty of any kind, express or
    implied, including but not limited to:

    ·  Fitness for a particular purpose
    ·  Merchantability
    ·  Non-infringement

    Andr3wOnTilt shall NOT be held liable for any damages, losses, claims, or
    issues arising from use of the Official Build, use of modified versions,
    distribution by third parties, or any derivative works.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

5.  VOID CLAUSE — UNAUTHORIZED REDISTRIBUTION

    If the Official Build (compiled and released by Andr3wOnTilt) is
    redistributed by third parties WITHOUT explicit written authorization,
    this EULA is considered VOID with respect to the unauthorized distributor,
    and all granted permissions are immediately revoked.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

6.  ACCEPTANCE

    By clicking "I Accept", you acknowledge that you have read, understood,
    and agreed to the terms of this End User License Agreement.

    By clicking "Decline", this software will not be configured and will exit.
    You may re-launch the application at any time to review and accept.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
© Andr3wOnTilt — All rights reserved.
"""


class EULAWindow(tk.Toplevel):
    def __init__(self, parent, pending_cfg: dict, on_accept):
        super().__init__(parent)
        self.pending_cfg = pending_cfg
        self.on_accept   = on_accept
        self.title("License Agreement")
        self.configure(bg=C["sidebar"])
        self.resizable(False, True)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._decline)
        self._build()
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w, h = 620, 560
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    def _build(self):
        hdr = tk.Frame(self, bg=C["surface"], pady=0)
        hdr.pack(fill="x", side="top")
        tk.Label(hdr, text="  📄  License Agreement",
                 font=("Segoe UI", 11, "bold"),
                 bg=C["surface"], fg=C["white"], pady=14).pack(anchor="w")
        tk.Frame(hdr, bg=C["border"], height=1).pack(fill="x")

        body = tk.Frame(self, bg=C["sidebar"])
        body.pack(fill="both", expand=True, padx=0, pady=0)

        text_outer = tk.Frame(body, bg=C["input"],
                              highlightthickness=1,
                              highlightbackground=C["border"])
        text_outer.pack(fill="both", expand=True, padx=20, pady=16)

        scroll = scrolledtext.ScrolledText(
            text_outer, bg=C["input"], fg=C["text"],
            font=("Consolas", 9), relief="flat", bd=0,
            state="normal", wrap="word", padx=16, pady=12,
            selectbackground=C["accent"])
        scroll.pack(fill="both", expand=True)
        scroll.insert("1.0", EULA_TEXT)
        scroll.configure(state="disabled")

        scroll.tag_add("header", "1.0", "4.0")
        scroll.tag_config("header", foreground=C["white"],
                          font=("Consolas", 10, "bold"))

        void_start = EULA_TEXT.find("5.  VOID CLAUSE")
        if void_start != -1:
            lb = EULA_TEXT[:void_start].count("\n") + 1
            scroll.tag_add("void", f"{lb}.0", f"{lb + 10}.end")
            scroll.tag_config("void", foreground=C["yellow"],
                              font=("Consolas", 9, "bold"))

        for marker in ("1.  OWNERSHIP", "2.  USE OF", "3.  MODIFICATION",
                       "4.  LIABILITY", "5.  VOID CLAUSE", "6.  ACCEPTANCE"):
            idx = EULA_TEXT.find(marker)
            if idx != -1:
                ln = EULA_TEXT[:idx].count("\n") + 1
                scroll.tag_add("section", f"{ln}.0", f"{ln}.end")
        scroll.tag_config("section", foreground=C["accent"],
                          font=("Consolas", 9, "bold"))

        foot = tk.Frame(self, bg=C["surface"])
        foot.pack(fill="x", side="bottom")
        tk.Frame(foot, bg=C["border"], height=1).pack(fill="x")

        btn_bar = tk.Frame(foot, bg=C["surface"])
        btn_bar.pack(fill="x", padx=20, pady=12)

        _styled_button(btn_bar, "✖  Decline", self._decline,
                       variant="ghost", padx=20, pady=10).pack(side="left")
        _styled_button(btn_bar, "✔  I Accept", self._accept,
                       variant="primary", padx=24, pady=10).pack(side="right")

    def _accept(self):
        save_config(self.pending_cfg)
        self.destroy()
        self.on_accept(self.pending_cfg)

    def _decline(self):
        self.destroy()


class Dashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        global _dashboard_ref, _lang
        _dashboard_ref = self

        self.withdraw()

        ok_d, err_d = _try_import_discord()
        _try_import_psutil()

        if not config_exists():
            self.deiconify()
            self.configure(bg=C["sidebar"])
            self.geometry("1x1")
            self.update()
            self.withdraw()
            SetupWizard(self, self._after_setup)
        else:
            cfg = load_config()
            set_lang(cfg.get("lang", "en"))
            self.update_idletasks()
            self._init_dashboard(cfg)

    def _after_setup(self, cfg):
        set_lang(cfg.get("lang", "en"))
        self._init_dashboard(cfg)

    def _init_dashboard(self, cfg):
        self.cfg        = cfg
        set_lang(cfg.get("lang", "en"))
        self.bot        = None
        self.bot_loop   = None
        self.bot_thread = None
        self.running    = False
        self._start_time = None
        self._pages:    dict[str, tk.Frame]  = {}
        self._nav_btns: dict[str, tk.Button] = {}
        self._cmd_text_widget = None

        self.title(f"{self.cfg.get('bot_name', 'Bot')} — {t('app_title')}")
        self.minsize(1000, 660)
        self.configure(bg=C["bg"])
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"1240x760+{(sw - 1240) // 2}+{(sh - 760) // 2}")
        self.deiconify()

        self._prefix_var = tk.StringVar(value=self.cfg.get("prefix", "!"))
        self._prefix_var.trace_add("write", self._on_prefix_change)

        self._build_ui()
        self._start_stats_loop()

        if not HAS_DISCORD:
            self.after(800, lambda: show_error_popup(
                self, "discord.py not found",
                f"Cannot import discord.py:\n{t('err_no_discord')}"))

    def _on_prefix_change(self, *_):
        try:
            new_prefix = self._prefix_var.get()
            if hasattr(self, "_cfg_prefix"):
                self._cfg_prefix.set(new_prefix)
            self._refresh_commands_page()
        except Exception:
            pass

    def _refresh_commands_page(self):
        try:
            if self._cmd_text_widget:
                self._populate_commands(self._cmd_text_widget)
        except Exception:
            pass

    def _build_ui(self):
        try:
            self._build_sidebar()
            self._build_dashboard_page()
            self._build_embed_page()
            self._build_music_page()
            self._build_commands_page()
            self._build_settings_page()
            self._show_page("dashboard")
        except Exception:
            tb = traceback.format_exc()
            root_logger.error(tb)
            self.after(100, lambda: show_error_popup(self, "UI Build Error", tb))

    def _build_sidebar(self):
        sb = tk.Frame(self, bg=C["sidebar"], width=240)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)

        top_bar = tk.Frame(sb, bg=C["sidebar"])
        top_bar.pack(fill="x", padx=14, pady=(18, 8))

        self.status_dot = tk.Label(top_bar, text="●", font=("Segoe UI", 13),
                                   bg=C["sidebar"], fg=C["offline"])
        self.status_dot.pack(side="left", padx=(0, 8))
        self.bot_name_lbl = tk.Label(top_bar, text=t("bot_offline"),
                                     font=("Segoe UI", 10, "bold"),
                                     bg=C["sidebar"], fg=C["white"])
        self.bot_name_lbl.pack(side="left")

        _divider(sb)
        tk.Frame(sb, bg=C["sidebar"], height=8).pack()

        tk.Label(sb, text="NAVIGATION", font=("Segoe UI", 8, "bold"),
                 bg=C["sidebar"], fg=C["muted"]).pack(anchor="w", padx=14, pady=(0, 4))

        for key, icon in [("dashboard", "⊞"), ("embeds", "◈"),
                          ("music",     "♪"), ("commands", "≡"),
                          ("settings",  "⚙")]:
            label = f"  {icon}   {t('nav_' + key)}"
            btn = tk.Button(sb, text=label, anchor="w", padx=10, pady=8,
                            bd=0, relief="flat", bg=C["sidebar"], fg=C["muted"],
                            activebackground=C["hover"], activeforeground=C["white"],
                            font=("Segoe UI", 9), cursor="hand2",
                            command=lambda k=key: self._show_page(k))
            btn.pack(fill="x", padx=6, pady=1)
            self._nav_btns[key] = btn

        tk.Frame(sb, bg=C["sidebar"]).pack(fill="both", expand=True)
        _divider(sb)

        ctrl = tk.Frame(sb, bg=C["sidebar"])
        ctrl.pack(fill="x", padx=10, pady=12)

        self.start_btn = _styled_button(ctrl, t("start_bot"), self.start_bot,
                                        variant="success", padx=0, pady=9)
        self.start_btn.configure(font=("Segoe UI", 9, "bold"), width=26)
        self.start_btn.pack(fill="x", pady=(0, 4))

        self.stop_btn = _styled_button(ctrl, t("stop_bot"), self.stop_bot,
                                       variant="danger", padx=0, pady=9)
        self.stop_btn.configure(font=("Segoe UI", 9, "bold"), width=26, state="disabled")
        self.stop_btn.pack(fill="x")

        self.content = tk.Frame(self, bg=C["bg"])
        self.content.pack(side="left", fill="both", expand=True)

    def _show_page(self, key: str):
        for f in self._pages.values():
            f.pack_forget()
        if key in self._pages:
            self._pages[key].pack(fill="both", expand=True)
        for k, b in self._nav_btns.items():
            active = k == key
            b.configure(
                bg=C["hover"] if active else C["sidebar"],
                fg=C["white"] if active else C["muted"],
            )

    def _page_header(self, parent, title_key, sub_key=None):
        hdr = tk.Frame(parent, bg=C["bg"])
        hdr.pack(fill="x", padx=28, pady=(22, 16))
        tk.Label(hdr, text=t(title_key), font=("Segoe UI", 16, "bold"),
                 bg=C["bg"], fg=C["white"]).pack(anchor="w")
        if sub_key:
            tk.Label(hdr, text=t(sub_key), font=("Segoe UI", 9),
                     bg=C["bg"], fg=C["muted"]).pack(anchor="w", pady=(2, 0))
        _divider(parent, C["surface"])

    def _stat_card(self, parent, title_key, init="—", color=None):
        color = color or C["accent"]
        card = tk.Frame(parent, bg=C["surface"], padx=18, pady=14)
        card.configure(highlightthickness=1, highlightbackground=C["border"])
        tk.Label(card, text=t(title_key), font=("Segoe UI", 8, "bold"),
                 bg=C["surface"], fg=C["muted"]).pack(anchor="w")
        tk.Label(card, text=init, font=("Segoe UI", 20, "bold"),
                 bg=C["surface"], fg=color).pack(anchor="w", pady=(4, 0))
        return card

    def _update_card(self, card, value, color):
        try:
            ch = card.winfo_children()
            if len(ch) >= 2:
                ch[1].configure(text=value, fg=color)
        except Exception:
            pass

    def _build_dashboard_page(self):
        page = tk.Frame(self.content, bg=C["bg"])
        self._pages["dashboard"] = page
        self._page_header(page, "dash_title", "dash_sub")

        cards_frame = tk.Frame(page, bg=C["bg"])
        cards_frame.pack(fill="x", padx=28, pady=(4, 0))

        self.card_ping    = self._stat_card(cards_frame, "card_ping",    "—",    C["accent"])
        self.card_servers = self._stat_card(cards_frame, "card_servers", "—",    C["green"])
        self.card_users   = self._stat_card(cards_frame, "card_users",   "—",    C["yellow"])
        self.card_uptime  = self._stat_card(cards_frame, "card_uptime",  "0s",   C["muted"])
        self.card_cpu     = self._stat_card(cards_frame, "card_cpu",     "—",    C["accent"])
        self.card_ram     = self._stat_card(cards_frame, "card_ram",     "—",    C["yellow"])

        for c in (self.card_ping, self.card_servers, self.card_users,
                  self.card_uptime, self.card_cpu, self.card_ram):
            c.pack(side="left", fill="x", expand=True, padx=(0, 8), ipady=4)

        pb_frame = tk.Frame(page, bg=C["bg"])
        pb_frame.pack(fill="x", padx=28, pady=(14, 0))
        s = ttk.Style()
        s.theme_use("default")
        for attr, clr in [("_pb_cpu", C["accent"]), ("_pb_ram", C["yellow"])]:
            sn = f"{attr}.Horizontal.TProgressbar"
            s.configure(sn, troughcolor=C["input"], background=clr, thickness=6)
            pb = ttk.Progressbar(pb_frame, style=sn, length=500,
                                  mode="determinate", maximum=100)
            pb.pack(side="left", padx=(0, 16))
            setattr(self, attr, pb)

        tk.Label(page, text=t("log_title"), font=("Segoe UI", 8, "bold"),
                 bg=C["bg"], fg=C["muted"]).pack(anchor="w", padx=28, pady=(18, 6))

        log_outer = tk.Frame(page, bg=C["surface"],
                             highlightthickness=1, highlightbackground=C["border"])
        log_outer.pack(fill="both", expand=True, padx=28, pady=(0, 22))

        self.log_box = scrolledtext.ScrolledText(
            log_outer, bg=C["input"], fg=C["text"],
            font=("Consolas", 9), relief="flat", bd=0,
            state="disabled", wrap="word", insertbackground=C["white"],
            padx=10, pady=8)
        self.log_box.pack(fill="both", expand=True)

        handler = TextWidgetHandler(self.log_box)
        handler.setFormatter(logging.Formatter("%(name)s  %(message)s"))
        root_logger.addHandler(handler)

    def _build_embed_page(self):
        page = tk.Frame(self.content, bg=C["bg"])
        self._pages["embeds"] = page
        self._page_header(page, "embed_title", "embed_sub")

        cols = tk.Frame(page, bg=C["bg"])
        cols.pack(fill="both", expand=True, padx=28, pady=16)
        left  = tk.Frame(cols, bg=C["bg"])
        left.pack(side="left", fill="both", expand=True, padx=(0, 20))
        right = tk.Frame(cols, bg=C["bg"])
        right.pack(side="left", fill="both", expand=True)

        self._eb = {k: tk.StringVar() for k in
                    ("title","desc","color","footer","image","thumb","author","channel","fname","fval")}
        self._eb["color"].set("#5865F2")
        self._eb_fields: list = []

        field_map = [
            ("eb_title",   "title",   None),
            ("eb_desc",    "desc",    None),
            ("eb_color",   "color",   None),
            ("eb_footer",  "footer",  None),
            ("eb_image",   "image",   None),
            ("eb_thumb",   "thumb",   None),
            ("eb_author",  "author",  None),
            ("eb_channel", "channel", None),
        ]
        for lbl_key, var_key, show in field_map:
            row = tk.Frame(left, bg=C["bg"])
            row.pack(fill="x", pady=3)
            tk.Label(row, text=t(lbl_key), font=("Segoe UI", 8, "bold"),
                     bg=C["bg"], fg=C["muted"], width=16, anchor="w").pack(side="left")
            _entry(row, self._eb[var_key], show=show, width=26).pack(side="left", fill="x", expand=True)

        tk.Label(left, text=t("eb_fields"), font=("Segoe UI", 8, "bold"),
                 bg=C["bg"], fg=C["muted"]).pack(anchor="w", pady=(14, 4))

        fr = tk.Frame(left, bg=C["bg"])
        fr.pack(fill="x")
        _entry(fr, self._eb["fname"], width=13).pack(side="left", padx=(0, 4))
        _entry(fr, self._eb["fval"],  width=17).pack(side="left")
        _styled_button(fr, t("eb_add"), self._add_field,
                       variant="primary", padx=10, pady=6).pack(side="left", padx=(6, 0))

        self._fields_lb = tk.Listbox(
            left, bg=C["input"], fg=C["text"], relief="flat",
            font=("Consolas", 8), height=3, selectbackground=C["accent"],
            highlightthickness=1, highlightbackground=C["border"])
        self._fields_lb.pack(fill="x", pady=6)

        _styled_button(left, t("eb_remove"), self._remove_field,
                       variant="ghost", padx=10, pady=5).pack(anchor="w")

        btn_row = tk.Frame(left, bg=C["bg"])
        btn_row.pack(fill="x", pady=(14, 0))
        _styled_button(btn_row, t("eb_preview"), self._draw_preview,
                       variant="default").pack(side="left", padx=(0, 6))
        _styled_button(btn_row, t("eb_send"), self._send_embed,
                       variant="primary").pack(side="left", padx=(0, 6))
        _styled_button(btn_row, t("eb_reset"), self._reset_embed,
                       variant="ghost").pack(side="left")

        preview_card = tk.Frame(right, bg=C["surface"],
                                highlightthickness=1, highlightbackground=C["border"],
                                padx=16, pady=14)
        preview_card.pack(fill="both", expand=True)
        tk.Label(preview_card, text=t("preview_label"), font=("Segoe UI", 8, "bold"),
                 bg=C["surface"], fg=C["muted"]).pack(anchor="w")
        self._preview_outer = tk.Frame(preview_card, bg=C["surface"])
        self._preview_outer.pack(fill="both", expand=True, pady=(10, 0))
        self._draw_preview()

    def _add_field(self):
        n = self._eb["fname"].get().strip()
        v = self._eb["fval"].get().strip()
        if n and v:
            self._eb_fields.append((n, v, False))
            self._fields_lb.insert("end", f"  {n}  →  {v}")
            self._eb["fname"].set(""); self._eb["fval"].set("")

    def _remove_field(self):
        sel = self._fields_lb.curselection()
        if sel:
            self._fields_lb.delete(sel[0])
            self._eb_fields.pop(sel[0])

    def _reset_embed(self):
        for k in ("title","desc","footer","image","thumb","author","channel"):
            self._eb[k].set("")
        self._eb["color"].set("#5865F2")
        self._eb_fields.clear()
        self._fields_lb.delete(0, "end")
        self._draw_preview()

    def _draw_preview(self):
        for w in self._preview_outer.winfo_children():
            w.destroy()
        try:
            h = self._eb["color"].get().lstrip("#")
            accent = f"#{h}" if len(h) == 6 and all(
                c in "0123456789abcdefABCDEF" for c in h) else C["accent"]
        except Exception:
            accent = C["accent"]

        outer = tk.Frame(self._preview_outer, bg=C["bg"])
        outer.pack(fill="both", expand=True)
        bar = tk.Frame(outer, bg=accent, width=4)
        bar.pack(side="left", fill="y")
        body = tk.Frame(outer, bg="#2b2d31", padx=14, pady=12)
        body.pack(side="left", fill="both", expand=True)
        tk.Label(body, text=self._eb["title"].get() or t("preview_default"),
                 font=("Segoe UI", 10, "bold"), bg="#2b2d31", fg=accent,
                 wraplength=280, justify="left").pack(anchor="w")
        if self._eb["desc"].get():
            tk.Label(body, text=self._eb["desc"].get(), font=("Segoe UI", 9),
                     bg="#2b2d31", fg=C["text"], wraplength=280, justify="left").pack(
                         anchor="w", pady=(4, 0))
        for fn, fv, _ in self._eb_fields:
            ff = tk.Frame(body, bg="#2b2d31")
            ff.pack(anchor="w", pady=3)
            tk.Label(ff, text=fn, font=("Segoe UI", 8, "bold"),
                     bg="#2b2d31", fg=C["text"]).pack(anchor="w")
            tk.Label(ff, text=fv, font=("Segoe UI", 8),
                     bg="#2b2d31", fg=C["muted"]).pack(anchor="w")
        if self._eb["footer"].get():
            _divider(body, "#3d4045")
            tk.Label(body, text=self._eb["footer"].get(), font=("Segoe UI", 8),
                     bg="#2b2d31", fg=C["muted"]).pack(anchor="w", pady=(6, 0))

    def _send_embed(self):
        if not HAS_DISCORD:
            messagebox.showerror("Error", t("err_no_discord")); return
        if not self.running or not self.bot:
            messagebox.showwarning("Offline", t("err_no_token")); return
        title = self._eb["title"].get().strip()
        ch    = self._eb["channel"].get().strip()
        if not title:
            messagebox.showerror("Error", t("err_title_req")); return
        if not ch:
            messagebox.showerror("Error", t("err_channel_req")); return
        try:
            color = int(self._eb["color"].get().lstrip("#"), 16)
        except Exception:
            color = 0x5865F2

        async def _do():
            try:
                channel = discord.utils.get(
                    (c for g in self.bot.guilds for c in g.text_channels), name=ch)
                if not channel:
                    root_logger.warning(t("err_channel_nf", ch=ch)); return
                em = discord.Embed(title=title,
                    description=self._eb["desc"].get().strip() or None, color=color)
                if self._eb["footer"].get(): em.set_footer(text=self._eb["footer"].get())
                if self._eb["image"].get():  em.set_image(url=self._eb["image"].get())
                if self._eb["thumb"].get():  em.set_thumbnail(url=self._eb["thumb"].get())
                if self._eb["author"].get(): em.set_author(name=self._eb["author"].get())
                for fn, fv, inl in self._eb_fields:
                    em.add_field(name=fn, value=fv, inline=inl)
                em.timestamp = discord.utils.utcnow()
                await channel.send(embed=em)
                root_logger.info(t("embed_sent", ch=ch))
            except Exception:
                tb = traceback.format_exc()
                root_logger.error(tb)
                self.after(0, lambda: show_error_popup(self, "Embed Error", tb))

        asyncio.run_coroutine_threadsafe(_do(), self.bot_loop)
        messagebox.showinfo("OK", t("embed_sending", ch=ch))

    def _build_music_page(self):
        page = tk.Frame(self.content, bg=C["bg"])
        self._pages["music"] = page
        self._page_header(page, "music_title", "music_sub")

        info_card = tk.Frame(page, bg=C["surface"],
                             highlightthickness=1, highlightbackground=C["border"],
                             padx=20, pady=16)
        info_card.pack(fill="x", padx=28, pady=16)
        tk.Label(info_card, text=t("music_info"), font=("Segoe UI", 11, "bold"),
                 bg=C["surface"], fg=C["white"]).pack(anchor="w")
        tk.Label(info_card, text=t("music_info2"), font=("Segoe UI", 9),
                 bg=C["surface"], fg=C["muted"]).pack(anchor="w", pady=(4, 0))

        tk.Label(page, text=t("music_cmds"), font=("Segoe UI", 8, "bold"),
                 bg=C["bg"], fg=C["muted"]).pack(anchor="w", padx=28, pady=(0, 6))

        cmds_wrap = tk.Frame(page, bg=C["surface"],
                             highlightthickness=1, highlightbackground=C["border"])
        cmds_wrap.pack(fill="x", padx=28)

        p = self._prefix_var.get()
        for i, (cmd, desc) in enumerate([
            (f"{p}play <query>",    "Play / queue a song from YouTube"),
            (f"{p}pause",          "Pause"),
            (f"{p}resume / {p}r",  "Resume"),
            (f"{p}skip / {p}s",    "Skip"),
            (f"{p}stop",           "Stop and disconnect"),
            (f"{p}queue / {p}q",   "Show queue"),
            (f"{p}volume <0-100>", "Set volume"),
            (f"{p}loop",           "Toggle loop"),
            (f"{p}nowplaying",     "Current song"),
            (f"{p}clear_queue",    "Clear queue"),
            (f"{p}join / {p}leave","Connect / Disconnect"),
        ]):
            bg = C["surface"] if i % 2 == 0 else C["surface2"]
            row = tk.Frame(cmds_wrap, bg=bg)
            row.pack(fill="x")
            tk.Label(row, text=cmd, font=("Consolas", 9, "bold"),
                     bg=bg, fg=C["accent"], width=26, anchor="w",
                     padx=14, pady=7).pack(side="left")
            tk.Label(row, text=desc, font=("Segoe UI", 9),
                     bg=bg, fg=C["muted"]).pack(side="left", padx=8)

    def _build_commands_page(self):
        page = tk.Frame(self.content, bg=C["bg"])
        self._pages["commands"] = page
        self._page_header(page, "cmd_title", "cmd_sub")

        outer = tk.Frame(page, bg=C["surface"],
                         highlightthickness=1, highlightbackground=C["border"])
        outer.pack(fill="both", expand=True, padx=28, pady=(4, 24))

        self._cmd_text_widget = scrolledtext.ScrolledText(
            outer, bg=C["input"], fg=C["text"],
            font=("Consolas", 10), relief="flat", bd=0,
            state="normal", padx=14, pady=12)
        self._cmd_text_widget.pack(fill="both", expand=True)
        self._populate_commands(self._cmd_text_widget)

    def _populate_commands(self, widget):
        p = self._prefix_var.get()
        widget.configure(state="normal")
        widget.delete("1.0", "end")

        categories = {
            t("cat_music"): [
                (f"{p}play <query>",       "Play or queue a song from YouTube"),
                (f"{p}pause",              "Pause playback"),
                (f"{p}resume / {p}r",      "Resume playback"),
                (f"{p}skip / {p}s",        "Skip current song"),
                (f"{p}stop",               "Stop and disconnect"),
                (f"{p}queue / {p}q",       "Show music queue"),
                (f"{p}volume <0-100>",     "Set volume"),
                (f"{p}loop",               "Toggle loop"),
                (f"{p}nowplaying / {p}np", "Currently playing"),
                (f"{p}clear_queue / {p}cq","Clear the queue"),
                (f"{p}join",               "Join voice channel"),
                (f"{p}leave / {p}dc",      "Leave voice channel"),
            ],
            t("cat_mod"): [
                (f"{p}kick @member",       "Kick a member"),
                (f"{p}ban @member",        "Ban a member"),
                (f"{p}unban <tag>",        "Remove ban"),
                (f"{p}mute @member <min>", "Mute for X minutes"),
                (f"{p}unmute @member",     "Unmute"),
                (f"{p}purge <n>",          "Delete n messages"),
                (f"{p}warn @member",       "Warn with DM"),
            ],
            t("cat_util"): [
                (f"{p}embed",              "Interactive embed builder"),
                (f"{p}quickembed T|D|C",   "Quick embed: Title|Desc|Color"),
                (f"{p}serverinfo",         "Server information"),
                (f"{p}userinfo [@member]", "User information"),
                (f"{p}botinfo",            "Bot information"),
                (f"{p}ping",               "Bot latency"),
                (f"{p}announce #channel",  "Send announcement"),
            ],
        }
        for cat, cmds in categories.items():
            widget.insert("end", f"\n  {cat}\n", "cat")
            widget.insert("end", "  " + "─" * 68 + "\n", "sep")
            for cmd, desc in cmds:
                widget.insert("end", f"  {cmd:<36}", "cmd")
                widget.insert("end", f"  {desc}\n", "desc")
            widget.insert("end", "\n")

        widget.tag_config("cat",  foreground=C["accent"], font=("Segoe UI", 10, "bold"))
        widget.tag_config("sep",  foreground=C["surface2"])
        widget.tag_config("cmd",  foreground=C["green"],  font=("Consolas", 10, "bold"))
        widget.tag_config("desc", foreground=C["muted"])
        widget.configure(state="disabled")

    def _build_settings_page(self):
        page = tk.Frame(self.content, bg=C["bg"])
        self._pages["settings"] = page
        self._page_header(page, "set_title", "set_sub")

        canvas    = tk.Canvas(page, bg=C["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(page, orient="vertical", command=canvas.yview)
        inner     = tk.Frame(canvas, bg=C["bg"])
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        _section_label(inner, "set_bot")

        self._cfg_token    = tk.StringVar(value=self.cfg.get("token", ""))
        self._cfg_botname  = tk.StringVar(value=self.cfg.get("bot_name", "MyBot"))
        self._cfg_prefix   = self._prefix_var
        self._cfg_activity = tk.StringVar(value=self.cfg.get("activity", ""))
        self._cfg_status   = tk.StringVar(value=self.cfg.get("status", "online"))

        for lbl_key, var, show in [
            ("set_token",    self._cfg_token,    "•"),
            ("set_botname",  self._cfg_botname,  None),
            ("set_prefix",   self._cfg_prefix,   None),
            ("set_activity", self._cfg_activity, None),
        ]:
            row = tk.Frame(inner, bg=C["bg"])
            row.pack(fill="x", padx=24, pady=4)
            tk.Label(row, text=t(lbl_key), font=("Segoe UI", 9, "bold"),
                     bg=C["bg"], fg=C["muted"], width=22, anchor="w").pack(side="left")
            _entry(row, var, show=show, width=34).pack(side="left")

        row_s = tk.Frame(inner, bg=C["bg"])
        row_s.pack(fill="x", padx=24, pady=4)
        tk.Label(row_s, text=t("set_status"), font=("Segoe UI", 9, "bold"),
                 bg=C["bg"], fg=C["muted"], width=22, anchor="w").pack(side="left")
        for s, lk, col in [("online","set_online",C["green"]),
                            ("idle",  "set_idle",  C["yellow"]),
                            ("dnd",   "set_dnd",   C["red"])]:
            tk.Radiobutton(row_s, text=t(lk), variable=self._cfg_status, value=s,
                           bg=C["bg"], fg=col, activebackground=C["bg"],
                           selectcolor=C["surface2"], font=("Segoe UI", 9),
                           cursor="hand2").pack(side="left", padx=(0, 14))

        _section_label(inner, "set_log")
        self._cfg_log_level = tk.StringVar(value=self.cfg.get("log_level", "INFO"))
        row_l = tk.Frame(inner, bg=C["bg"])
        row_l.pack(fill="x", padx=24, pady=4)
        tk.Label(row_l, text=t("set_loglevel"), font=("Segoe UI", 9, "bold"),
                 bg=C["bg"], fg=C["muted"], width=22, anchor="w").pack(side="left")
        for lvl in ("DEBUG","INFO","WARNING","ERROR"):
            tk.Radiobutton(row_l, text=lvl, variable=self._cfg_log_level, value=lvl,
                           bg=C["bg"], fg=C["text"], activebackground=C["bg"],
                           selectcolor=C["surface2"], font=("Segoe UI", 9),
                           cursor="hand2").pack(side="left", padx=(0, 12))

        _section_label(inner, "set_lang")
        self._cfg_lang = tk.StringVar(value=self.cfg.get("lang", "en"))
        row_lang = tk.Frame(inner, bg=C["bg"])
        row_lang.pack(fill="x", padx=24, pady=4)
        tk.Label(row_lang, text=t("set_lang_label"), font=("Segoe UI", 9, "bold"),
                 bg=C["bg"], fg=C["muted"], width=22, anchor="w").pack(side="left")
        for code, name in [("en","English"), ("it","Italiano"), ("pl","Polski")]:
            tk.Radiobutton(row_lang, text=name, variable=self._cfg_lang, value=code,
                           bg=C["bg"], fg=C["text"], activebackground=C["bg"],
                           selectcolor=C["surface2"], font=("Segoe UI", 9),
                           cursor="hand2").pack(side="left", padx=(0, 14))

        _section_label(inner, "set_deps")
        tk.Label(inner,
                 text="  pip install discord.py[voice] yt-dlp psutil PyNaCl",
                 font=("Consolas", 9), bg=C["input"], fg=C["text"],
                 padx=14, pady=8).pack(fill="x", padx=24, pady=4)

        intents_card = tk.Frame(inner, bg=C["surface2"], padx=14, pady=10)
        intents_card.pack(fill="x", padx=24, pady=4)
        tk.Label(intents_card, text=t("set_intents"), font=("Segoe UI", 9),
                 bg=C["surface2"], fg=C["yellow"], justify="left",
                 wraplength=660).pack(anchor="w")

        tk.Frame(inner, bg=C["bg"], height=16).pack()
        _styled_button(inner, t("set_save"), self._save_settings,
                       variant="primary", padx=24, pady=10
                       ).pack(padx=24, anchor="w")
        tk.Frame(inner, bg=C["bg"], height=40).pack()

    def _save_settings(self):
        self.cfg["token"]     = self._cfg_token.get().strip()
        self.cfg["bot_name"]  = self._cfg_botname.get().strip() or "MyBot"
        self.cfg["prefix"]    = self._cfg_prefix.get().strip() or "!"
        self.cfg["activity"]  = self._cfg_activity.get().strip()
        self.cfg["status"]    = self._cfg_status.get()
        self.cfg["log_level"] = self._cfg_log_level.get()
        self.cfg["lang"]      = self._cfg_lang.get()
        save_config(self.cfg)

        set_lang(self.cfg["lang"])
        root_logger.setLevel(self.cfg["log_level"])

        self._prefix_var.set(self.cfg["prefix"])
        self.title(f"{self.cfg['bot_name']} — {t('app_title')}")

        messagebox.showinfo(t("saved_title"), t("saved_msg"))

    def start_bot(self):
        if not HAS_DISCORD:
            messagebox.showerror("Error", t("err_no_discord")); return
        token = self.cfg.get("token", "").strip()
        if not token:
            messagebox.showerror("Error", t("err_no_token"))
            self._show_page("settings"); return
        if self.running:
            messagebox.showinfo("Info", t("err_already_run")); return

        try:
            self.bot      = self._create_bot()
            self.bot_loop = asyncio.new_event_loop()
        except Exception:
            tb = traceback.format_exc()
            root_logger.error(tb)
            show_error_popup(self, "Bot Init Error", tb); return

        async def _runner():
            for ext in ("musicManager","administrationManager"):
                try:
                    await self.bot.load_extension(ext)
                    root_logger.info(t("ext_loaded", ext=ext))
                except Exception:
                    tb = traceback.format_exc()
                    root_logger.error(tb)
                    self.after(0, lambda t_=tb, e=ext: show_error_popup(
                        self, f"Extension Error: {e}", t_))
            await self.bot.start(token)

        def _run():
            asyncio.set_event_loop(self.bot_loop)
            try:
                self.bot_loop.run_until_complete(_runner())
            except Exception as e:
                tb = traceback.format_exc()
                if "Improper token" in str(e) or "LoginFailure" in type(e).__name__:
                    self.after(0, lambda: show_error_popup(
                        self, "Invalid Token", t("token_invalid")))
                else:
                    root_logger.error(tb)
                    self.after(0, lambda: show_error_popup(self, "Bot Error", tb))
            finally:
                self.running = False
                self.after(0, self._on_bot_stopped)

        self.bot_thread = threading.Thread(target=_run, daemon=True)
        self.bot_thread.start()
        self.running     = True
        self._start_time = time.time()
        self._on_bot_started()

    def _create_bot(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members          = True
        intents.voice_states     = True
        bot = commands.Bot(command_prefix=self.cfg["prefix"], intents=intents)
        cfg = self.cfg

        @bot.event
        async def on_ready():
            try:
                act = cfg.get("activity", "") or f"{cfg['prefix']}help"
                await bot.change_presence(
                    status=discord.Status[cfg.get("status","online")],
                    activity=discord.Game(name=act))
                root_logger.info(f"🤖  {bot.user}  (ID: {bot.user.id})")
            except Exception:
                root_logger.error(traceback.format_exc())

        @bot.event
        async def on_command_error(ctx, error):
            root_logger.warning(f"[cmd:{ctx.command}] {error}")

        return bot

    def stop_bot(self):
        if not self.running or not self.bot: return
        async def _s():
            try: await self.bot.close()
            except Exception: pass
        asyncio.run_coroutine_threadsafe(_s(), self.bot_loop)

    def _on_bot_started(self):
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.status_dot.configure(fg=C["idle"])
        self.bot_name_lbl.configure(text=t("connecting"))
        root_logger.info(t("bot_starting"))

    def _on_bot_stopped(self):
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.status_dot.configure(fg=C["offline"])
        self.bot_name_lbl.configure(text=t("bot_offline"))
        self.bot = self.bot_loop = None
        root_logger.info(t("bot_stopped"))

    def _start_stats_loop(self):
        self._update_stats()

    def _update_stats(self):
        try:
            if self.bot and self.running and self.bot.is_ready():
                ping  = round(self.bot.latency * 1000)
                p_col = C["green"] if ping < 100 else (C["yellow"] if ping < 200 else C["red"])
                self._update_card(self.card_ping,    f"{ping} ms", p_col)
                self._update_card(self.card_servers, str(len(self.bot.guilds)), C["green"])
                self._update_card(self.card_users,
                    str(sum(g.member_count for g in self.bot.guilds)), C["yellow"])
                self.bot_name_lbl.configure(
                    text=str(self.bot.user).split("#")[0] if self.bot.user else "Online")
                self.status_dot.configure(fg=C["online"])

            if self._start_time and self.running:
                e = int(time.time() - self._start_time)
                h, r = divmod(e, 3600); m, s = divmod(r, 60)
                self._update_card(self.card_uptime,
                    f"{h}h {m}m {s}s" if h else (f"{m}m {s}s" if m else f"{s}s"), C["muted"])

            if HAS_PSUTIL:
                cpu = psutil.cpu_percent()
                ram = psutil.virtual_memory()
                self._update_card(self.card_cpu, f"{cpu:.0f}%",
                    C["green"] if cpu < 60 else (C["yellow"] if cpu < 85 else C["red"]))
                self._update_card(self.card_ram,
                    f"{ram.percent:.0f}%",
                    C["green"] if ram.percent < 70 else C["yellow"])
                try:
                    self._pb_cpu["value"] = cpu
                    self._pb_ram["value"] = ram.percent
                except Exception:
                    pass
        except Exception:
            pass
        self.after(2000, self._update_stats)


if __name__ == "__main__":
    try:
        app = Dashboard()
        app.mainloop()
    except Exception:
        tb = traceback.format_exc()
        try:
            _r = tk.Tk(); _r.withdraw()
            messagebox.showerror("Fatal Error", tb)
            _r.destroy()
        except Exception:
            print(tb, file=sys.stderr)
        sys.exit(1)