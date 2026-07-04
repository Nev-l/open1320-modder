"""
Nitto Legends Mod Installer
Fetches a manifest from nitto.lol and installs car mod files into the
correct game cache folders.  Works on Windows and macOS.
"""
VERSION = "0.0.1"

import os
import sys
import json
import struct
import zlib
import threading
import urllib.request
import urllib.error
import io

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from PIL import Image, ImageTk

# ── Paths ──────────────────────────────────────────────────────────────────────

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

GAME_DIR     = os.path.normpath(os.path.join(BASE_DIR, ".."))
CACHE_DIR    = os.path.join(GAME_DIR, "cache")
CAR_DIR      = os.path.join(CACHE_DIR, "car")
PACKAGES_DIR = os.path.join(CAR_DIR,  "packages")
WHEEL_DIR    = os.path.join(CAR_DIR,  "wheel")

# ── Server ─────────────────────────────────────────────────────────────────────

SERVER       = "http://nitto.lol:8184"
MANIFEST_URL = SERVER + "/mods/manifest.json"
MANIFEST_ALL = SERVER + "/mods/manifest-all.json"
RIMS_MANI_URL = SERVER + "/mods/rims/manifest.json"

# ── Theme ──────────────────────────────────────────────────────────────────────

BG   = "#0a0a1a"
DARK = "#0f0f2e"
FG   = "#e0e0e0"
ACC  = "#00d4ff"
MID  = "#16213e"
WARN = "#ff9900"


def _get(url: str, timeout: int = 15, extra_headers: dict = None) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "NittoModInstaller/1.0"})
    if extra_headers:
        for k, v in extra_headers.items():
            req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _post(url: str, data: bytes, content_type="application/json",
          extra_headers: dict = None, timeout: int = 15) -> bytes:
    req = urllib.request.Request(url, data=data, method="POST",
                                  headers={"User-Agent":    "NittoModInstaller/1.0",
                                           "Content-Type":  content_type,
                                           "Content-Length": str(len(data))})
    if extra_headers:
        for k, v in extra_headers.items():
            req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


# ── SWF image extractor ────────────────────────────────────────────────────────

def _image_from_swf(data: bytes) -> "Image.Image | None":
    """Extract first displayable image from raw SWF bytes without external tools."""
    try:
        if len(data) < 8:
            return None
        sig = data[:3]
        if sig == b"CWS":
            data = b"FWS" + data[3:8] + zlib.decompress(data[8:])
        elif sig != b"FWS":
            return None

        # Skip SWF header: sig(3) + ver(1) + fileLen(4) + RECT(variable) + frameRate(2) + frameCount(2)
        pos    = 8
        nbits  = (data[pos] >> 3) & 0x1F
        rbytes = (5 + 4 * nbits + 7) // 8
        pos   += rbytes + 4   # RECT + frameRate + frameCount

        while pos + 2 <= len(data):
            hdr      = struct.unpack_from("<H", data, pos)[0]
            pos     += 2
            tag_type = hdr >> 6
            tag_len  = hdr & 0x3F
            if tag_len == 0x3F:
                if pos + 4 > len(data):
                    break
                tag_len = struct.unpack_from("<i", data, pos)[0]
                pos += 4
            td  = data[pos: pos + tag_len]
            pos += tag_len

            if tag_type == 0:   # End
                break

            # DefineBitsJPEG2 (21): charId(2) + jpeg
            if tag_type == 21 and len(td) > 2:
                try:
                    return Image.open(io.BytesIO(td[2:])).convert("RGBA")
                except Exception:
                    pass

            # DefineBitsJPEG3 (35): charId(2) + alphaOffset(4) + jpeg + alphaData
            if tag_type == 35 and len(td) > 6:
                try:
                    aoff = struct.unpack_from("<I", td, 2)[0]
                    return Image.open(io.BytesIO(td[6: 6 + aoff])).convert("RGBA")
                except Exception:
                    pass

            # DefineBitsLossless2 (36): charId(2) + fmt(1) + w(2) + h(2) + [colorTableSize(1)] + zlibData
            if tag_type == 36 and len(td) > 7:
                try:
                    fmt = td[2]
                    w   = struct.unpack_from("<H", td, 3)[0]
                    h   = struct.unpack_from("<H", td, 5)[0]
                    off = 7 if fmt == 3 else 7   # skip colorTableSize byte if palette
                    raw = zlib.decompress(td[off:])
                    if fmt == 5:   # ARGB32
                        arr = bytearray(w * h * 4)
                        for i in range(w * h):
                            a, r, g, b = raw[i*4], raw[i*4+1], raw[i*4+2], raw[i*4+3]
                            arr[i*4:i*4+4] = bytes([r, g, b, a])
                        return Image.frombytes("RGBA", (w, h), bytes(arr))
                except Exception:
                    pass
    except Exception:
        pass
    return None


# ── Main window ────────────────────────────────────────────────────────────────

class InstallerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Nitto Legends — Mod Installer v{VERSION}")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(900, 580)

        self._manifest    = None
        self._cars        = []
        self._chk_vars    = {}
        self._rims        = []
        self._rim_chk     = {}
        self._prev_tk     = None
        self._installing  = False
        self._admin_mode  = False
        self._admin_key   = ""

        self._style()
        self._build_ui()
        self.after(200, self._fetch_manifest)

    # ── Style ──────────────────────────────────────────────────────────────────

    def _style(self):
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except Exception:
            pass
        s.configure(".",              background=BG, foreground=FG,
                    fieldbackground=MID, troughcolor=DARK, borderwidth=0)
        s.configure("TLabel",         background=BG,  foreground=FG)
        s.configure("TFrame",         background=BG)
        s.configure("TLabelframe",    background=BG,  foreground=ACC, bordercolor="#333")
        s.configure("TLabelframe.Label", background=BG, foreground=ACC,
                    font=("Segoe UI", 9, "bold"))
        s.configure("TButton",        background=MID, foreground=FG, padding=6)
        s.configure("Accent.TButton", background=ACC, foreground=DARK,
                    font=("Segoe UI", 9, "bold"), padding=6)
        s.configure("Warn.TButton",   background=WARN, foreground=DARK,
                    font=("Segoe UI", 9, "bold"), padding=6)
        s.map("TButton",        background=[("active", "#1a2a4a")])
        s.map("Accent.TButton", background=[("active", "#00aacc")])
        s.map("Warn.TButton",   background=[("active", "#cc7700")])
        s.configure("TProgressbar", troughcolor=DARK, background=ACC,
                    bordercolor=BG, lightcolor=ACC, darkcolor=ACC)
        s.configure("TCheckbutton", background=BG, foreground=FG)
        s.configure("Treeview",     background=MID, foreground=FG,
                    fieldbackground=MID, rowheight=28)
        s.configure("Treeview.Heading", background="#0f3460", foreground=ACC,
                    font=("Segoe UI", 8, "bold"))
        s.map("Treeview", background=[("selected", "#0f3460")],
              foreground=[("selected", ACC)])

    # ── UI ─────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # Header
        hdr = tk.Frame(self, bg="#0f3460", pady=10)
        hdr.grid(row=0, column=0, sticky="ew")
        tk.Label(hdr, text="Nitto Legends  —  Mod Installer",
                 bg="#0f3460", fg=ACC,
                 font=("Segoe UI", 16, "bold")).pack(side="left", padx=16)
        self._server_lbl = tk.Label(hdr, text="Connecting to nitto.lol…",
                                     bg="#0f3460", fg="#aaa", font=("Segoe UI", 8))
        self._server_lbl.pack(side="left", padx=8)
        self._admin_btn = tk.Button(hdr, text="Admin Mode",
                                     bg="#333", fg="#aaa",
                                     font=("Segoe UI", 8), relief="flat",
                                     padx=8, pady=4, command=self._toggle_admin)
        ttk.Button(hdr, text="Refresh",
                   command=self._fetch_manifest).pack(side="right", padx=(0, 12))
        self._admin_btn.pack(side="right", padx=(0, 4))

        # Body
        body = ttk.Frame(self, padding=10)
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=0)
        body.rowconfigure(0, weight=1)

        # Tabs: Cars | Rims
        nb = ttk.Notebook(body)
        nb.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        # ── Cars tab ──────────────────────────────────────────────────────────
        cars_tab = ttk.Frame(nb, padding=4)
        nb.add(cars_tab, text="  Cars  ")
        cars_tab.rowconfigure(1, weight=1)
        cars_tab.columnconfigure(0, weight=1)

        sel_fr = ttk.Frame(cars_tab)
        sel_fr.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        ttk.Button(sel_fr, text="Select All",  command=self._select_all).pack(side="left", padx=(0, 4))
        ttk.Button(sel_fr, text="Select None", command=self._select_none).pack(side="left")
        self._count_lbl = ttk.Label(sel_fr, text="", foreground="#666", font=("Segoe UI", 8))
        self._count_lbl.pack(side="right")

        cols = ("sel", "name", "author", "version", "size", "status")
        self._tree = ttk.Treeview(cars_tab, columns=cols, show="headings", selectmode="browse")
        for c, w, lbl in [("sel",40,""),("name",200,"Car Name"),("author",110,"Author"),
                           ("version",60,"Version"),("size",70,"Size"),("status",100,"Status")]:
            self._tree.heading(c, text=lbl)
            self._tree.column(c, width=w, minwidth=w, stretch=(c == "name"))
        self._tree.grid(row=1, column=0, sticky="nsew")
        sb = ttk.Scrollbar(cars_tab, orient="vertical", command=self._tree.yview)
        sb.grid(row=1, column=1, sticky="ns")
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self._tree.bind("<Button-1>",         self._on_tree_click)

        # ── Rims tab ──────────────────────────────────────────────────────────
        rims_tab = ttk.Frame(nb, padding=4)
        nb.add(rims_tab, text="  Rims  ")
        rims_tab.rowconfigure(1, weight=1)
        rims_tab.columnconfigure(0, weight=1)

        rim_sel_fr = ttk.Frame(rims_tab)
        rim_sel_fr.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        ttk.Button(rim_sel_fr, text="Select All",
                   command=self._rim_select_all).pack(side="left", padx=(0, 4))
        ttk.Button(rim_sel_fr, text="Select None",
                   command=self._rim_select_none).pack(side="left")
        self._rim_count_lbl = ttk.Label(rim_sel_fr, text="", foreground="#666",
                                         font=("Segoe UI", 8))
        self._rim_count_lbl.pack(side="right")

        rim_cols = ("sel", "name", "author", "rim_id", "size", "status")
        self._rim_tree = ttk.Treeview(rims_tab, columns=rim_cols, show="headings",
                                       selectmode="browse")
        for c, w, lbl in [("sel",40,""),("name",200,"Pack Name"),("author",110,"Author"),
                           ("rim_id",70,"Rim Slot"),("size",70,"Size"),("status",100,"Status")]:
            self._rim_tree.heading(c, text=lbl)
            self._rim_tree.column(c, width=w, minwidth=w, stretch=(c == "name"))
        self._rim_tree.grid(row=1, column=0, sticky="nsew")
        rim_sb = ttk.Scrollbar(rims_tab, orient="vertical", command=self._rim_tree.yview)
        rim_sb.grid(row=1, column=1, sticky="ns")
        self._rim_tree.configure(yscrollcommand=rim_sb.set)
        self._rim_tree.bind("<<TreeviewSelect>>", self._on_rim_select)
        self._rim_tree.bind("<Button-1>",         self._on_rim_click)

        # Right panel
        right = ttk.Frame(body, width=240)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)

        prev_lf = ttk.LabelFrame(right, text="Preview", padding=4)
        prev_lf.pack(fill="x")
        self._prev_cv = tk.Canvas(prev_lf, width=220, height=140,
                                   bg=DARK, highlightthickness=0)
        self._prev_cv.pack()
        self._prev_cv.create_text(110, 70, text="Select a car",
                                   fill="#444", font=("Segoe UI", 9), tags="ph")

        info_lf = ttk.LabelFrame(right, text="Details", padding=8)
        info_lf.pack(fill="x", pady=(8, 0))
        self._info_text = tk.Text(info_lf, width=28, height=5,
                                   bg=MID, fg=FG, relief="flat",
                                   font=("Segoe UI", 8), state="disabled",
                                   wrap="word", cursor="arrow")
        self._info_text.pack(fill="both")

        # Admin: editable name (hidden until admin mode)
        self._name_lf = ttk.LabelFrame(right, text="Edit Car Name (Admin)", padding=8)
        self._edit_name = tk.StringVar()
        ttk.Entry(self._name_lf, textvariable=self._edit_name).pack(fill="x")
        ttk.Button(self._name_lf, text="Save Name to Server",
                    command=self._save_name).pack(fill="x", pady=(4, 0))
        self._name_status = ttk.Label(self._name_lf, text="", foreground="#aaa",
                                       font=("Segoe UI", 7))
        self._name_status.pack(anchor="w")

        # Admin: test install panel (hidden until admin mode)
        self._test_lf = ttk.LabelFrame(right, text="Test Install", padding=8)
        tk.Label(self._test_lf,
                  text="Install as car ID\n(temporarily replaces that car in-game):",
                  bg=BG, fg=WARN, font=("Segoe UI", 8), wraplength=210, justify="left"
                  ).pack(anchor="w")
        id_fr = ttk.Frame(self._test_lf)
        id_fr.pack(fill="x", pady=(4, 0))
        tk.Label(id_fr, text="Target ID:", bg=BG, fg=FG, font=("Segoe UI", 8)).pack(side="left")
        self._test_id = tk.IntVar(value=80)
        tk.Spinbox(id_fr, textvariable=self._test_id, from_=1, to=999, width=6,
                    bg=MID, fg=ACC, relief="flat", font=("Consolas", 9)).pack(side="left", padx=(4,0))
        ttk.Button(self._test_lf, text="Test Install (temporary)",
                    style="Warn.TButton",
                    command=self._test_install_selected).pack(fill="x", pady=(6, 0))

        path_lf = ttk.LabelFrame(right, text="Install Location", padding=8)
        path_lf.pack(fill="x", pady=(8, 0))
        tk.Label(path_lf, text=CACHE_DIR, bg=BG, fg="#666",
                  font=("Consolas", 7), wraplength=220, justify="left").pack(anchor="w")

        # Bottom bar
        bot = tk.Frame(self, bg=BG, pady=8)
        bot.grid(row=2, column=0, sticky="ew")
        bot.columnconfigure(2, weight=1)
        ttk.Button(bot, text="Install Cars", style="Accent.TButton",
                   command=self._install_selected).grid(row=0, column=0, padx=(12, 4))
        ttk.Button(bot, text="Install Rims", style="Accent.TButton",
                   command=self._install_rims_selected).grid(row=0, column=1, padx=(0, 8))
        self._prog = ttk.Progressbar(bot, mode="determinate", length=400)
        self._prog.grid(row=0, column=2, sticky="ew", padx=(0, 8))
        self._status = tk.StringVar(value="Ready.")
        tk.Label(bot, textvariable=self._status, bg=BG, fg="#aaa",
                  font=("Segoe UI", 8), anchor="w").grid(
            row=1, column=0, columnspan=4, sticky="ew", padx=12, pady=(4, 0))

        # Log
        log_lf = ttk.LabelFrame(self, text="Log", padding=4)
        log_lf.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 10))
        self._log = tk.Text(log_lf, height=5, bg=DARK, fg="#888",
                             font=("Consolas", 7), relief="flat", state="disabled")
        self._log.pack(fill="x")

    # ── Admin mode ─────────────────────────────────────────────────────────────

    def _toggle_admin(self):
        if self._admin_mode:
            self._admin_mode = False
            self._admin_key  = ""
            self._admin_btn.config(text="Admin Mode", bg="#333", fg="#aaa")
            self._name_lf.pack_forget()
            self._test_lf.pack_forget()
            self._fetch_manifest()
            return

        pwd = simpledialog.askstring("Admin Mode", "Enter admin password:",
                                      show="*", parent=self)
        if not pwd:
            return
        # Validate password server-side
        self._admin_btn.config(text="Checking…", bg="#333", fg="#aaa")
        threading.Thread(target=self._check_admin_pw, args=(pwd,), daemon=True).start()

    def _check_admin_pw(self, pwd: str):
        try:
            body = json.dumps({"password": pwd}).encode()
            resp = json.loads(_post(SERVER + "/mods/admin/auth", body))
            if resp.get("ok"):
                self.after(0, lambda: self._on_admin_ok(pwd))
            else:
                self.after(0, self._on_admin_fail)
        except Exception as e:
            self.after(0, lambda: self._on_admin_fail(str(e)))

    def _on_admin_ok(self, pwd: str):
        self._admin_mode = True
        self._admin_key  = pwd
        self._admin_btn.config(text="Admin Mode ON", bg=WARN, fg=DARK)
        self._name_lf.pack(fill="x", pady=(8, 0), before=self._test_lf
                           if self._test_lf.winfo_ismapped() else None)
        # Re-pack in correct order
        self._name_lf.pack(fill="x", pady=(8, 0))
        self._test_lf.pack(fill="x", pady=(8, 0))
        self._fetch_manifest()

    def _on_admin_fail(self, err=""):
        self._admin_btn.config(text="Admin Mode", bg="#333", fg="#aaa")
        msg = "Incorrect password." + (f"\n\n{err}" if err else "")
        messagebox.showerror("Wrong password", msg, parent=self)

    # ── Manifest fetch ─────────────────────────────────────────────────────────

    def _fetch_manifest(self):
        self._server_lbl.config(text="Connecting…", fg="#aaa")
        url     = MANIFEST_ALL if self._admin_mode else MANIFEST_URL
        headers = {"X-Admin-Key": self._admin_key} if self._admin_mode else {}
        self._log_line("Fetching manifest" + (" (admin)" if self._admin_mode else ""))
        threading.Thread(target=self._fetch_worker,
                          args=(url, headers), daemon=True).start()
        threading.Thread(target=self._fetch_rims_worker, daemon=True).start()

    def _fetch_worker(self, url, headers):
        try:
            data     = _get(url, extra_headers=headers)
            manifest = json.loads(data.decode("utf-8"))
            self.after(0, lambda: self._on_manifest(manifest))
        except Exception as e:
            self.after(0, lambda: self._on_manifest_error(str(e)))

    def _on_manifest(self, manifest):
        self._manifest = manifest
        self._cars     = manifest.get("cars", [])
        pub   = sum(1 for c in self._cars if not c.get("test"))
        tests = sum(1 for c in self._cars if c.get("test"))
        lbl   = f"Connected  |  {pub} public"
        if tests:
            lbl += f"  |  {tests} test"
        self._server_lbl.config(text=lbl, fg="#aaa")
        self._log_line(f"Manifest: {pub} public, {tests} test car(s).")
        self._populate_tree()

    def _on_manifest_error(self, err):
        self._server_lbl.config(text=f"Error: {err}", fg="#e94560")
        self._log_line(f"ERROR: {err}")
        messagebox.showerror("Connection Error",
                              f"Could not fetch mod list:\n\n{err}", parent=self)

    # ── Rims manifest ──────────────────────────────────────────────────────────

    def _fetch_rims_worker(self):
        try:
            data     = _get(RIMS_MANI_URL)
            manifest = json.loads(data.decode("utf-8"))
            self.after(0, lambda: self._on_rims_manifest(manifest))
        except Exception as e:
            self.after(0, lambda: self._log_line(f"Rims: {e}"))

    def _on_rims_manifest(self, manifest):
        self._rims = manifest.get("rims", [])
        self._log_line(f"Rims manifest: {len(self._rims)} pack(s).")
        self._populate_rim_tree()

    def _populate_rim_tree(self):
        for iid in self._rim_tree.get_children():
            self._rim_tree.delete(iid)
        self._rim_chk.clear()
        for pack in self._rims:
            pid    = pack["id"]
            status = self._rim_install_status(pack)
            var    = tk.BooleanVar(value=False)
            self._rim_chk[pid] = var
            tag    = "installed" if status == "Installed" else ""
            self._rim_tree.insert("", "end", iid=pid,
                values=("☐", pack.get("name", pid), pack.get("author", "—"),
                        str(pack.get("rim_id", "?")), _human_size(pack.get("total_bytes", 0)),
                        status),
                tags=(tag,))
        self._rim_tree.tag_configure("installed", foreground="#00c87a")
        self._rim_count_lbl.config(text="")

    def _rim_install_status(self, pack):
        rid   = pack.get("rim_id", 0)
        files = pack.get("files", [])
        if not files or not rid:
            return "—"
        dest = os.path.join(WHEEL_DIR, f"wheelFF_{rid}.swf")
        return "Installed" if os.path.exists(dest) else "Not installed"

    def _on_rim_click(self, evt):
        col = self._rim_tree.identify_column(evt.x)
        iid = self._rim_tree.identify_row(evt.y)
        if not iid:
            return
        var = self._rim_chk.get(iid)
        if var:
            var.set(not var.get())
            vals = list(self._rim_tree.item(iid, "values"))
            vals[0] = "☑" if var.get() else "☐"
            self._rim_tree.item(iid, values=vals)
            n = sum(1 for v in self._rim_chk.values() if v.get())
            self._rim_count_lbl.config(text=f"{n} selected")

    def _on_rim_select(self, *_):
        sel = self._rim_tree.selection()
        if not sel:
            return
        pack = next((p for p in self._rims if p["id"] == sel[0]), None)
        if not pack:
            return
        lines = [
            f"Name:    {pack.get('name','—')}",
            f"Author:  {pack.get('author','—')}",
            f"Rim slot:{pack.get('rim_id','—')}",
            f"Files:   {len(pack.get('files',[]))}",
            f"Version: {pack.get('version','1.0')}",
        ]
        desc = pack.get("description", "")
        if desc:
            lines += ["", desc]
        self._info_text.configure(state="normal")
        self._info_text.delete("1.0", "end")
        self._info_text.insert("1.0", "\n".join(lines))
        self._info_text.configure(state="disabled")

        # Load preview — prefer wheelFF, fall back to first available file
        files = pack.get("files", [])
        preview_file = (
            next((f for f in files if "wheelff" in f.lower()), None)
            or next((f for f in files), None)
        )
        if preview_file:
            url = f"{SERVER}/mods/rims/{pack['id']}/{preview_file}"
            threading.Thread(target=self._load_preview_swf,
                              args=(url, {}), daemon=True).start()
        else:
            self._clear_preview("No preview")

    def _rim_select_all(self):
        for iid in self._rim_tree.get_children():
            v = self._rim_chk.get(iid)
            if v:
                v.set(True)
                vals = list(self._rim_tree.item(iid, "values"))
                vals[0] = "☑"
                self._rim_tree.item(iid, values=vals)
        n = sum(1 for v in self._rim_chk.values() if v.get())
        self._rim_count_lbl.config(text=f"{n} selected")

    def _rim_select_none(self):
        for iid in self._rim_tree.get_children():
            v = self._rim_chk.get(iid)
            if v:
                v.set(False)
                vals = list(self._rim_tree.item(iid, "values"))
                vals[0] = "☐"
                self._rim_tree.item(iid, values=vals)
        self._rim_count_lbl.config(text="0 selected")

    def _install_rims_selected(self):
        if self._installing:
            return
        selected = [p for p in self._rims if self._rim_chk.get(p["id"], tk.BooleanVar()).get()]
        if not selected:
            messagebox.showinfo("Nothing selected", "Tick at least one rim pack.", parent=self)
            return
        if not messagebox.askyesno("Confirm install",
                f"Install {len(selected)} rim pack(s) into:\n{WHEEL_DIR}\n\nContinue?",
                parent=self):
            return
        self._installing = True
        threading.Thread(target=self._install_rims_worker,
                          args=(selected,), daemon=True).start()

    def _install_rims_worker(self, packs):
        os.makedirs(WHEEL_DIR, exist_ok=True)
        total  = sum(len(p.get("files", [])) for p in packs)
        done   = 0
        errors = []
        base   = SERVER + "/mods"
        VIEW_MAP = {"wheelFF": "FF", "wheelFR": "FR", "wheelBF": "BF", "wheelBR": "BR",
                    "wheelR": "BF"}

        for pack in packs:
            pid   = pack["id"]
            rid   = pack.get("rim_id", 0)
            name  = pack.get("name", pid)
            files = pack.get("files", [])
            self._set_status(f"Installing {name}…")
            self._log_line(f"\n[Rim: {name}] slot {rid}")

            for fname in files:
                # Determine which game view file this maps to
                stem = fname.replace(".swf", "").lower()
                dest_name = None
                for hint, view in VIEW_MAP.items():
                    if hint.lower() in stem:
                        dest_name = f"wheel{view}_{rid}.swf"
                        break
                if dest_name is None:
                    dest_name = fname  # keep original if no hint

                url  = f"{base}/rims/{pid}/{fname}"
                dest = os.path.join(WHEEL_DIR, dest_name)
                try:
                    self._log_line(f"  {fname} → {dest_name}…")
                    data = _get(url)
                    with open(dest, "wb") as f:
                        f.write(data)
                except Exception as e:
                    self._log_line(f"  ERROR: {e}")
                    errors.append(f"{name}/{fname}: {e}")
                done += 1
                self._set_prog(done, total)

            # Refresh row
            self.after(0, lambda p=pack: self._refresh_rim_row(p))

        self._installing = False
        if errors:
            self._set_status(f"Done with {len(errors)} error(s).")
            self.after(0, lambda: messagebox.showwarning(
                "Install complete", f"{len(errors)} error(s):\n" + "\n".join(errors), parent=self))
        else:
            self._set_status(f"{len(packs)} rim pack(s) installed.")
            self.after(0, lambda: messagebox.showinfo(
                "Installed", f"{len(packs)} rim pack(s) installed into:\n{WHEEL_DIR}", parent=self))

    def _refresh_rim_row(self, pack):
        pid = pack["id"]
        if self._rim_tree.exists(pid):
            vals    = list(self._rim_tree.item(pid, "values"))
            status  = self._rim_install_status(pack)
            vals[5] = status
            self._rim_tree.item(pid, values=vals,
                                 tags=("installed",) if status == "Installed" else ())

    # ── Tree ───────────────────────────────────────────────────────────────────

    def _populate_tree(self):
        for iid in self._tree.get_children():
            self._tree.delete(iid)
        self._chk_vars.clear()
        for car in self._cars:
            cid     = str(car["id"])
            is_test = car.get("test", False)
            name    = ("[TEST] " if is_test else "") + car.get("name", f"Car {cid}")
            status  = self._install_status(car)
            var     = tk.BooleanVar(value=False)
            self._chk_vars[cid] = var
            tag     = "test" if is_test else ("installed" if status == "Installed" else "")
            self._tree.insert("", "end", iid=cid,
                               values=("☐", name, car.get("author","—"),
                                       car.get("version","1.0"),
                                       _human_size(car.get("total_bytes",0)),
                                       status),
                               tags=(tag,))
        self._tree.tag_configure("installed", foreground="#00c87a")
        self._tree.tag_configure("test",      foreground=WARN)
        self._update_count()

    def _install_status(self, car):
        files = car.get("files", [])
        if not files:
            return "—"
        dest = _dest_path(str(car["id"]), files[0])
        return "Installed" if dest and os.path.exists(dest) else "Not installed"

    def _on_tree_click(self, evt):
        col = self._tree.identify_column(evt.x)
        iid = self._tree.identify_row(evt.y)
        if not iid:
            return
        var = self._chk_vars.get(iid)
        if var:
            var.set(not var.get())
            vals = list(self._tree.item(iid, "values"))
            vals[0] = "☑" if var.get() else "☐"
            self._tree.item(iid, values=vals)
            self._update_count()

    def _on_tree_select(self, *_):
        sel = self._tree.selection()
        if not sel:
            return
        car = next((c for c in self._cars if str(c["id"]) == sel[0]), None)
        if car:
            self._show_detail(car)

    def _show_detail(self, car):
        is_test = car.get("test", False)
        lines   = [
            f"Name:    {car.get('name','—')}",
            f"Author:  {car.get('author','—')}",
            f"Version: {car.get('version','—')}",
            f"Files:   {len(car.get('files',[]))}",
            f"Status:  {'[TEST BUILD]' if is_test else 'Public'}",
        ]
        desc = car.get("description", "")
        if desc:
            lines += ["", desc]
        self._info_text.configure(state="normal")
        self._info_text.delete("1.0", "end")
        self._info_text.insert("1.0", "\n".join(lines))
        self._info_text.configure(state="disabled")

        # Populate edit name field in admin mode
        if self._admin_mode:
            self._edit_name.set(car.get("name", ""))
            self._name_status.config(text=f"Car ID: {car['id']}")

        # Load preview — prefer packages/{id}f/body.swf, fallback {id}b/body.swf
        cid     = str(car["id"])
        is_test = car.get("test", False)
        headers = {"X-Admin-Key": self._admin_key} if (self._admin_mode or is_test) else {}
        files   = car.get("files", [])
        body_rel = (
            next((f for f in files if f.endswith("/body.swf") and f"/{cid}f/" in f), None)
            or next((f for f in files if f.endswith("/body.swf") and f"/{cid}b/" in f), None)
            or next((f for f in files if f.endswith("/body.swf")), None)
        )
        if body_rel:
            body_url = f"{SERVER}/mods/cars/{cid}/{body_rel}"
            threading.Thread(target=self._load_preview_swf,
                              args=(body_url, headers), daemon=True).start()
        else:
            self._clear_preview("No preview")

    def _load_preview_swf(self, url, headers):
        try:
            data = _get(url, timeout=10, extra_headers=headers)
            img  = _image_from_swf(data)
            if img:
                img.thumbnail((220, 140), Image.LANCZOS)
                tkimg = ImageTk.PhotoImage(img)
                self.after(0, lambda: self._show_preview(tkimg))
                return
        except Exception:
            pass
        self.after(0, lambda: self._clear_preview("No preview"))

    def _load_preview_png(self, url, headers):
        try:
            data  = _get(url, timeout=8, extra_headers=headers)
            img   = Image.open(io.BytesIO(data)).convert("RGBA")
            img.thumbnail((220, 140), Image.LANCZOS)
            tkimg = ImageTk.PhotoImage(img)
            self.after(0, lambda: self._show_preview(tkimg))
        except Exception:
            self.after(0, lambda: self._clear_preview("No preview"))

    def _show_preview(self, tkimg):
        self._prev_cv.delete("all")
        self._prev_tk = tkimg
        self._prev_cv.create_image(110, 70, anchor="center", image=tkimg)

    def _clear_preview(self, msg="Select a car"):
        self._prev_cv.delete("all")
        self._prev_cv.create_text(110, 70, text=msg, fill="#444", font=("Segoe UI", 9))

    # ── Admin: save name ───────────────────────────────────────────────────────

    def _save_name(self):
        sel = self._tree.selection()
        if not sel:
            messagebox.showinfo("No car selected", "Select a car first.", parent=self)
            return
        cid  = sel[0]
        name = self._edit_name.get().strip()
        if not name:
            messagebox.showinfo("Empty name", "Enter a name first.", parent=self)
            return
        self._name_status.config(text="Saving…")
        threading.Thread(target=self._save_name_worker,
                          args=(cid, name), daemon=True).start()

    def _save_name_worker(self, cid, name):
        try:
            body = json.dumps({"car_id": int(cid), "name": name}).encode()
            resp = json.loads(_post(
                SERVER + "/mods/admin/update-meta", body,
                extra_headers={"X-Admin-Key": self._admin_key}))
            if resp.get("ok"):
                # Update local manifest
                for car in self._cars:
                    if str(car["id"]) == cid:
                        car["name"] = name
                self.after(0, lambda: self._on_name_saved(cid, name))
            else:
                self.after(0, lambda: self._name_status.config(
                    text=f"Error: {resp.get('error','?')}", foreground="#e94560"))
        except Exception as e:
            self.after(0, lambda: self._name_status.config(
                text=f"Error: {e}", foreground="#e94560"))

    def _on_name_saved(self, cid, name):
        self._name_status.config(text="Saved!", foreground="#00c87a")
        # Update the tree row
        if self._tree.exists(cid):
            vals    = list(self._tree.item(cid, "values"))
            is_test = next((c.get("test") for c in self._cars if str(c["id"]) == cid), False)
            vals[1] = ("[TEST] " if is_test else "") + name
            self._tree.item(cid, values=vals)

    # ── Select all / none ──────────────────────────────────────────────────────

    def _select_all(self):
        for iid in self._tree.get_children():
            v = self._chk_vars.get(iid)
            if v:
                v.set(True)
                vals = list(self._tree.item(iid, "values"))
                vals[0] = "☑"
                self._tree.item(iid, values=vals)
        self._update_count()

    def _select_none(self):
        for iid in self._tree.get_children():
            v = self._chk_vars.get(iid)
            if v:
                v.set(False)
                vals = list(self._tree.item(iid, "values"))
                vals[0] = "☐"
                self._tree.item(iid, values=vals)
        self._update_count()

    def _update_count(self):
        n = sum(1 for v in self._chk_vars.values() if v.get())
        self._count_lbl.config(text=f"{n} selected")

    # ── Install ────────────────────────────────────────────────────────────────

    def _get_selected_cars(self):
        return [c for c in self._cars
                if self._chk_vars.get(str(c["id"]), tk.BooleanVar()).get()]

    def _install_selected(self):
        if self._installing:
            return
        selected = self._get_selected_cars()
        if not selected:
            messagebox.showinfo("Nothing selected", "Tick at least one car.", parent=self)
            return
        if not messagebox.askyesno("Confirm install",
                                    f"Install {len(selected)} car mod(s) into:\n{CACHE_DIR}\n\nContinue?",
                                    parent=self):
            return
        self._installing = True
        threading.Thread(target=self._install_worker,
                          args=(selected, None), daemon=True).start()

    def _test_install_selected(self):
        if self._installing:
            return
        selected = self._get_selected_cars()
        if not selected:
            messagebox.showinfo("Nothing selected", "Tick a car first.", parent=self)
            return
        if len(selected) > 1:
            messagebox.showwarning("Test install",
                                    "Test install works on one car at a time.", parent=self)
            return
        car       = selected[0]
        target_id = self._test_id.get()
        if not messagebox.askyesno("Test Install",
                f"Temporarily install [{car.get('name')}] as car ID {target_id}.\n\n"
                f"This REPLACES car {target_id} in your game cache.\n\nContinue?",
                parent=self):
            return
        self._installing = True
        threading.Thread(target=self._install_worker,
                          args=([car], target_id), daemon=True).start()

    def _install_worker(self, cars, test_as_id):
        base_url   = (self._manifest or {}).get("base_url", SERVER + "/mods")
        dl_headers = {"X-Admin-Key": self._admin_key} if self._admin_mode else {}
        total      = sum(len(c.get("files", [])) for c in cars)
        done       = 0
        errors     = []

        for car in cars:
            real_id    = car["id"]
            install_id = test_as_id if test_as_id is not None else real_id
            name       = car.get("name", f"Car {real_id}")
            files      = car.get("files", [])
            self._set_status(f"Installing {name}…")
            self._log_line(f"\n[{name}]" + (f" → as car {install_id}" if test_as_id else ""))

            for rel_path in files:
                dest_rel = _remap_car_id(rel_path, str(real_id), str(install_id)) \
                           if test_as_id else rel_path
                url  = f"{base_url}/cars/{real_id}/{rel_path}"
                dest = _dest_path(str(install_id), dest_rel)
                if not dest:
                    done += 1
                    self._set_prog(done, total)
                    continue
                try:
                    self._log_line(f"  {rel_path}…")
                    data = _get(url, extra_headers=dl_headers)
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    with open(dest, "wb") as f:
                        f.write(data)
                except Exception as e:
                    self._log_line(f"  ERROR: {e}")
                    errors.append(f"{name}/{rel_path}: {e}")
                done += 1
                self._set_prog(done, total)

            self.after(0, lambda c=car: self._refresh_row(c))

        self._installing = False
        if errors:
            self._set_status(f"Done with {len(errors)} error(s).")
            self.after(0, lambda: messagebox.showwarning(
                "Install complete",
                f"{len(errors)} error(s):\n" + "\n".join(errors), parent=self))
        elif test_as_id:
            self._set_status(f"Test install complete — shows as car {test_as_id} in game.")
            self.after(0, lambda: messagebox.showinfo(
                "Test install complete",
                f"Car installed as ID {test_as_id}.\nLaunch the game and check car {test_as_id}.",
                parent=self))
        else:
            self._set_status(f"All {len(cars)} car(s) installed.")
            self.after(0, lambda: messagebox.showinfo(
                "Install complete",
                f"{len(cars)} car mod(s) installed into:\n{CACHE_DIR}", parent=self))

    def _refresh_row(self, car):
        cid = str(car["id"])
        if self._tree.exists(cid):
            vals    = list(self._tree.item(cid, "values"))
            status  = self._install_status(car)
            vals[5] = status
            self._tree.item(cid, values=vals,
                             tags=("installed",) if status == "Installed" else ())

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _set_status(self, msg):
        self.after(0, lambda: self._status.set(msg))

    def _set_prog(self, done, total):
        pct = int(done / total * 100) if total else 100
        self.after(0, lambda: self._prog.configure(value=pct))

    def _log_line(self, msg):
        def _a():
            self._log.configure(state="normal")
            self._log.insert("end", msg + "\n")
            self._log.see("end")
            self._log.configure(state="disabled")
        self.after(0, _a)


# ── Path helpers ───────────────────────────────────────────────────────────────

def _dest_path(car_id: str, rel_path: str) -> "str | None":
    rel_path = rel_path.replace("\\", "/").lstrip("/")
    return os.path.normpath(os.path.join(CAR_DIR, rel_path))


def _remap_car_id(rel_path: str, src_id: str, dst_id: str) -> str:
    return rel_path.replace(src_id, dst_id)


def _human_size(nbytes: int) -> str:
    if nbytes <= 0:
        return "—"
    for unit in ("B", "KB", "MB", "GB"):
        if nbytes < 1024:
            return f"{nbytes:.0f} {unit}"
        nbytes /= 1024
    return f"{nbytes:.1f} GB"


if __name__ == "__main__":
    InstallerApp().mainloop()
