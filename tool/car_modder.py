"""
1320 Legends Car Modder
Per-part image editing, custom image upload, overlay alignment, and badge editor.
"""
VERSION = "0.0.1"
import os, sys, shutil, tempfile, threading, math, dataclasses, json, tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from PIL import Image, ImageTk, ImageDraw
import numpy as np

if getattr(sys, "frozen", False):
    BASE_DIR    = os.path.dirname(sys.executable)
    _BUNDLE_DIR = sys._MEIPASS
else:
    BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
    _BUNDLE_DIR = BASE_DIR

GAME_DIR         = os.path.normpath(os.path.join(BASE_DIR, ".."))
CACHE_DIR        = os.path.join(GAME_DIR, "cache")
PACKAGES_DIR     = os.path.join(CACHE_DIR, "car", "packages")
CAR_DIR          = os.path.join(CACHE_DIR, "car")
OUTPUT_DIR       = os.path.join(BASE_DIR, "output")

sys.path.insert(0, _BUNDLE_DIR)
import swf_utils
from swf_utils import (get_package_info, list_visual_swfs, export_image,
                        export_all_images, replace_all_images_in_swf, should_recolor,
                        export_badge_images, add_badges_to_swf, get_swf_badge_gap_ids,
                        set_ffdec_path, find_ffdec_default, build_part_swf,
                        parse_tire_swf, patch_tire_swf, swf_rect_origin,
                        read_swf_info)
from color_utils import apply_color_adjustments

CONFIG_FILE = os.path.join(BASE_DIR, "1320modder_config.json")


def _load_config() -> dict:
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_config(cfg: dict):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass

CARS = {
    1:"Acura Integra GSR",2:"Mitsubishi Lancer Evo VIII",3:"Ford Mustang GT",
    4:"Infiniti G35 Coupe",5:"Ford GT",6:"Acura RSX Type-S",7:"Chevy Corvette C6",
    8:"Honda Integra Type R",9:"Honda S2000",10:"Dodge Viper",11:"STI Drag-Spec",
    13:"Scion tC",14:"Toyota Supra",15:"Dodge Neon SRT-4",16:"Mazda RX-7",
    17:"Mazda RX-7 Drag Spec",18:"Chevy Camaro",19:"Mazdaspeed 6 Bergenholtz",
    20:"NOS Endurance tC",21:"Nissan GT-R",22:"Scion xB",23:"Mazdaspeed 3",
    24:"Mazda RX-8",25:"Nissan 350Z",26:"Royal Purple Nissan Z",28:"Acura NSX",
    29:"Acura NSX Race Edition",30:"Scion tC TRD Challenge",31:"Honda Civic Si",
    32:"Ford Mustang Boss 302",33:"Pontiac Solstice GXP",34:"Chevy Corvette Z06",
    35:"Nissan 300ZX",36:"Chevy Corvette Z06",37:"Honda Civic Si",
    38:"Nissan Skyline GT-R",39:"SEMA Series Camaro",40:"Tire Buyer Nissan GT-R",
    41:"Nissan 240SX",42:"Royal Purple ZR1",43:"Pontiac GTO",
    44:"Honda Prelude DOHC VTEC",45:"Ford SVT Cobra R",46:"Chevy Camaro SS",
    47:"Nissan Sentra SE-R",48:"Chevy Camaro SS",49:"Pontiac Trans Am",
    50:"Pontiac GTO",51:"Infiniti G37S",52:"Chevy Cobalt SS",53:"Nissan 240SX",
    54:"Ford Mustang GT 2010",55:"Nissan 370Z",56:"Pontiac GTO Judge",
    57:"Mazda Furai",58:"VW Golf R32",59:"Dodge Challenger SRT-8",
    60:"Dodge Charger SRT-8",61:"Toyota MR2",62:"VW Beetle",
    63:"Dodge Challenger R/T",64:"VW Golf GTI",65:"Toyota Celica GT-S",
    66:"Supercharged ZR1",67:"VW Golf GTI",68:"Ford Shelby GT500",
    69:"SEMA Ford Mustang",70:"IvD Battle Challenger",71:"IvD Battle 240SX",
    72:"Buick Grand National",73:"Mazda RX-3",74:"Honda CR-X Si",
    75:"Dodge Charger R/T",76:"Honda Civic Si",77:"VW Corrado",
    78:"Ford F-150 SVT Lightning",79:"Plymouth 'Cuda",80:"Plymouth Road Runner",
    81:"Dodge Ram SRT-10",82:"Chevy C-10",83:"Chevy S-10",84:"VW Jetta GLI",
    85:"Pontiac Firebird Trans Am",86:"Drag Spec Camaro",87:"Mitsubishi Lancer Evo X",
    88:"Mitsubishi Eclipse GSX",89:"Subaru Impreza WRX STI",90:"McLaren MP4-12C",
    91:"Subaru Impreza WRX STI",92:"Subaru Impreza WRX STI",94:"Hellion Mustang",
    95:"Scion tC",97:"Dodge Charger SRT-8",98:"McLaren MP4-12C VTW",
    99:"Toyota Corolla GT-S",100:"Chevy Impala SS",101:"SLR McLaren LE I",
    102:"SLR McLaren LE II",104:"SEMA Challenger",105:"Honda Civic Type R",
    106:"Nissan Cube",107:"Mazda MX-5 Miata",109:"Dodge Viper ACR-X",
    110:"SLR McLaren Speed Greetings",111:"STI Year of the Dragon",
    112:"STI Year of the Dragon II",113:"Scion FR-S",114:"Toyota MR2 Spyder Widebody",
    115:"Toyota MR2 Spyder",116:"Challenger 1320",117:"AMC Javelin",118:"SLR 722 GT",
    119:"Scion FR-S Widebody IvsD2",120:"Bergenholtz Mazda RX-8",121:"Box",
    122:"Toyota Starlet",123:"McLaren F1 GTR",124:"Dodge Viper SRT-10",
    125:"Nissan Skyline GT-R",126:"Ford Mustang Beast",127:"Ford Focus RS",
    128:"Hyundai Genesis Coupe",129:"Ram SRT-10",131:"Ford Grand Torino",
    133:"Scion FR-S Widebody",134:"Plymouth 'Cuda",135:"Pontiac GTO",
    136:"Porsche 911 GT3 RS",137:"Hyundai Veloster Turbo",138:"Ford Fiesta ST",
    139:"Dodge Charger SuperBee",140:"Porsche Panamera Turbo",141:"Ford RS200",
    142:"Mazdaspeed 3",143:"Ford Falcon GT",144:"Ford Deuce Coupe",
    145:"Toyota Celica GT 2000",146:"Ford Deuce Coupe Gold",
    147:"Ford Deuce Coupe Champion",148:"Porsche 911 RWB",149:"Ford Taurus SHO",
    150:"RWB Ramintra 993R",153:"SignalR Concept",155:"Dodge Viper YOTS Black",
    156:"Dodge Viper YOTS Red",158:"RWB Stella",159:"Top Fool Dragster",
    160:"RWB Rotana 993",
}

COLOR_PRESETS = {
    "Original":(0,1.0,1.0), "Black":(0,0.0,0.12), "White":(0,0.0,2.5),
    "Red":(0,1.5,1.0),      "Blue":(200,1.4,0.9),  "Green":(100,1.4,0.9),
    "Gold":(40,1.5,1.0),    "Purple":(270,1.4,0.9),"Orange":(20,1.5,1.0),
    "Greyscale":(0,0.0,1.0),"Custom":None,
}

BG, FG, ACC, DARK = "#1a1a2e", "#e0e0e0", "#00d4ff", "#0d0d1a"


# ── Data model ────────────────────────────────────────────────────────────────

class ImageSlot:
    def __init__(self, swf_path:str, char_id:int, orig_path:str, label:str):
        self.swf_path   = swf_path
        self.char_id    = char_id
        self.orig_path  = orig_path
        self.label      = label
        self.custom_path: str|None = None
        # per-slot color adjustments
        self.hue  = 0.0
        self.sat  = 1.0
        self.bri  = 1.0
        self._orig_cache: Image.Image|None = None
        # decal layers — list of {'path', 'x', 'y', 'scale', 'alpha', 'name'}
        self.decals: list[dict] = []

    def orig_image(self) -> Image.Image:
        if self._orig_cache is None:
            self._orig_cache = Image.open(self.orig_path).convert("RGBA")
        return self._orig_cache

    def source_image(self) -> Image.Image:
        if self.custom_path:
            return Image.open(self.custom_path).convert("RGBA")
        return self.orig_image()

    def final_image(self) -> Image.Image:
        """Source image with color adjustments and all decals composited."""
        img = apply_color_adjustments(self.source_image(), self.hue, self.sat, self.bri)
        for d in self.decals:
            if not d.get('path') or not os.path.exists(d['path']):
                continue
            try:
                decal = Image.open(d['path']).convert("RGBA")
                scale = d.get('scale', 1.0)
                if scale != 1.0:
                    nw = max(1, int(decal.width * scale))
                    nh = max(1, int(decal.height * scale))
                    decal = decal.resize((nw, nh), Image.LANCZOS)
                alpha = d.get('alpha', 1.0)
                if alpha < 1.0:
                    r, g, b, a = decal.split()
                    a = a.point(lambda v: int(v * alpha))
                    decal = Image.merge("RGBA", (r, g, b, a))
                out = img.copy()
                out.paste(decal, (d.get('x', 0), d.get('y', 0)), decal)
                img = out
            except Exception:
                pass
        return img

    @property
    def is_modified(self) -> bool:
        return (self.custom_path is not None or bool(self.decals) or
                self.hue != 0 or self.sat != 1.0 or self.bri != 1.0)


# ── Wheel position preview window ─────────────────────────────────────────────

class WheelPreviewWindow(tk.Toplevel):
    """Visual wheel position editor with real tire/wheel image overlays."""

    STAGE_W, STAGE_H = 640, 400
    CANVAS_SCALE = 1.5          # visual scale — game coords stay 640×400
    HANDLE_R   = 12
    HANDLE_HIT = 20
    TIRE_COLORS = {'F': '#00d4ff', 'R': '#ff6b6b', 'Back': '#00ff88'}

    def __init__(self, parent, slots: list, wheel_vars: dict,
                 wheel_src: dict, pkg_info: dict, car_id: int, tmp_dir: str,
                 plate_vars: dict = None, plate_src: dict = None):
        super().__init__(parent, bg=BG)
        self.title("Wheel & Plate Aligner — drag circles to reposition")
        self.resizable(False, False)
        self._slots     = slots
        self._wvars     = wheel_vars   # {(view,tire): {tx,ty}: DoubleVar}
        self._wsrc      = wheel_src    # {(view,tire): {tx,ty,scx,scy}: raw values
        self._pvars     = plate_vars or {}   # {p1..p4: {tx,ty}: DoubleVar}
        self._psrc      = plate_src  or {}   # {p1..p4: {tx,ty,...}: raw values
        self._pkg_info  = pkg_info
        self._car_id    = car_id
        self._tmp_dir   = tmp_dir
        self._view      = tk.StringVar(value='f')
        self._drag      = None
        self._tk_img    = None
        self._tk_bg     = None
        self._tk_ovls   = []           # keep PhotoImage refs alive
        self._cids      = {}
        self._body_off  = {}           # view -> (xmin, ymin) from body SWF RECT
        self._body_size = {}           # view -> (width_px, height_px) from body SWF RECT
        self._overlays  = {}           # (view,layer,tire) -> PIL.Image
        self._loading    = False
        self._tire_id    = tk.IntVar(value=1)
        self._wheel_id   = tk.IntVar(value=1)
        self._show_tire  = tk.BooleanVar(value=True)
        self._show_wheel = tk.BooleanVar(value=True)
        # Per-position visibility: each can be toggled independently
        self._show_pos   = {
            'F':    tk.BooleanVar(value=True),
            'R':    tk.BooleanVar(value=True),
            'Back': tk.BooleanVar(value=True),
        }
        self._ov_status  = tk.StringVar(value='Click "Load" to show tire/wheel images')

        self._build_ui()
        self._render()

    # ── Setup ─────────────────────────────────────────────────────────────────

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.resizable(True, True)
        # Use grid on the Toplevel so every row is always visible
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)   # canvas row expands

        # ── ROW 0: Load Tires / Rims bar ─────────────────────────────────────
        load_fr = ttk.LabelFrame(self, text="Load Tires / Rims", padding=8)
        load_fr.grid(row=0, column=0, sticky='ew', padx=8, pady=(8, 4))

        ttk.Label(load_fr, text="Tire ID (1-7):").grid(row=0, column=0, sticky='w')
        ttk.Spinbox(load_fr, textvariable=self._tire_id, from_=1, to=7,
                    width=5).grid(row=0, column=1, sticky='w', padx=(4, 16))

        ttk.Label(load_fr, text="Rim ID (1-157):").grid(row=0, column=2, sticky='w')
        ttk.Spinbox(load_fr, textvariable=self._wheel_id, from_=1, to=157,
                    width=5).grid(row=0, column=3, sticky='w', padx=(4, 16))

        ttk.Checkbutton(load_fr, text="Show Tires",
                        variable=self._show_tire,
                        command=self._render).grid(row=0, column=4, padx=(0, 8))
        ttk.Checkbutton(load_fr, text="Show Rims",
                        variable=self._show_wheel,
                        command=self._render).grid(row=0, column=5, padx=(0, 16))

        ttk.Button(load_fr, text="LOAD", width=10, style="Accent.TButton",
                   command=self._load_overlays).grid(row=0, column=6, padx=(0, 4))

        ttk.Label(load_fr, textvariable=self._ov_status,
                  foreground='#aaa', font=('Segoe UI', 8),
                  width=40).grid(row=0, column=7, sticky='w', padx=(8, 0))

        # View toggle
        view_fr = ttk.Frame(load_fr)
        view_fr.grid(row=1, column=0, columnspan=8, sticky='w', pady=(6, 0))
        ttk.Label(view_fr, text="View:").pack(side='left', padx=(0, 4))
        for v, t in [('f', 'Front'), ('b', 'Back')]:
            ttk.Radiobutton(view_fr, text=t, value=v, variable=self._view,
                            command=self._on_view_change).pack(side='left', padx=(0, 8))

        # ── ROW 1: canvas (left) + position table (right) ────────────────────
        mid = tk.Frame(self, bg=BG)
        mid.grid(row=1, column=0, sticky='nsew', padx=8, pady=4)
        mid.columnconfigure(1, weight=1)
        mid.rowconfigure(0, weight=1)

        cs = self.CANVAS_SCALE
        self._cv = tk.Canvas(mid, width=int(self.STAGE_W * cs), height=int(self.STAGE_H * cs),
                             bg=DARK, highlightthickness=0, cursor='crosshair')
        self._cv.grid(row=0, column=0, sticky='nw')
        self._cv.bind('<ButtonPress-1>',   self._on_press)
        self._cv.bind('<B1-Motion>',       self._on_drag)
        self._cv.bind('<ButtonRelease-1>', self._on_release)
        self._cv.bind('<Left>',  lambda e: self._nudge(-1,  0))
        self._cv.bind('<Right>', lambda e: self._nudge( 1,  0))
        self._cv.bind('<Up>',    lambda e: self._nudge( 0, -1))
        self._cv.bind('<Down>',  lambda e: self._nudge( 0,  1))
        self._cv.bind('<shift-Left>',  lambda e: self._nudge(-10,   0))
        self._cv.bind('<shift-Right>', lambda e: self._nudge( 10,   0))
        self._cv.bind('<shift-Up>',    lambda e: self._nudge(  0, -10))
        self._cv.bind('<shift-Down>',  lambda e: self._nudge(  0,  10))
        self._cv.config(takefocus=True)

        # Position + size table (right of canvas) — all 5 wheel positions, both views
        right = tk.Frame(mid, bg=BG)
        right.grid(row=0, column=1, sticky='ns', padx=(10, 0))

        pos_lf = ttk.LabelFrame(right, text="Wheel Positions & Size", padding=(8, 4))
        pos_lf.pack(fill='x')

        # Visibility toggles
        vis_fr = ttk.Frame(pos_lf)
        vis_fr.grid(row=0, column=0, columnspan=6, sticky='w', pady=(0, 4))
        ttk.Label(vis_fr, text='Show:', foreground='#888',
                  font=('Segoe UI', 7)).pack(side='left', padx=(0, 4))
        self._pos_chks = {}
        for tire, label in [('F', 'Front'), ('R', 'Rear'), ('Back', 'Race-rear')]:
            ck = ttk.Checkbutton(vis_fr, text=label,
                                 variable=self._show_pos[tire], command=self._render)
            ck.pack(side='left', padx=(0, 6))
            self._pos_chks[tire] = ck

        def _spin(parent, dv, lo, hi, w=5):
            sp = tk.Spinbox(parent, textvariable=dv, from_=lo, to=hi, increment=1,
                            width=w, bg="#16213e", fg=ACC, buttonbackground="#0f3460",
                            relief="flat", font=("Consolas", 8))
            dv.trace_add('write', lambda *_: self.after(0, self._render))
            return sp

        def _wheel_block(parent_row, view):
            vu = view.upper()
            # Section divider
            sep_fr = ttk.Frame(pos_lf)
            sep_fr.grid(row=parent_row, column=0, columnspan=2, sticky='ew', pady=(6, 2))
            ttk.Label(sep_fr, text=f'— {vu} View —', foreground='#555',
                      font=('Segoe UI', 7, 'bold')).pack(side='left')

            tires = [('F', 'Front wheel'), ('R', 'Rear wheel')]
            if view == 'b':
                tires.append(('Back', 'Race rear'))

            r = parent_row + 1
            for tire, lbl in tires:
                wkey  = (view, tire)
                vars_ = self._wvars.get(wkey, {vn: tk.DoubleVar(
                    value=100 if vn in ('scx','scy') else 0)
                    for vn in ('tx','ty','scx','scy')})

                # Row A: ● label   X:[  ]  Y:[  ]
                row_a = ttk.Frame(pos_lf)
                row_a.grid(row=r, column=0, columnspan=2, sticky='w', pady=(3, 0))
                tk.Label(row_a, text='●', fg=self.TIRE_COLORS[tire],
                         bg=BG, font=('Segoe UI', 9)).pack(side='left')
                ttk.Label(row_a, text=lbl, font=('Segoe UI', 8),
                          width=11).pack(side='left', padx=(2, 6))
                ttk.Label(row_a, text='X:').pack(side='left')
                _spin(row_a, vars_['tx'], -9999, 9999, 6).pack(side='left', padx=(2, 6))
                ttk.Label(row_a, text='Y:').pack(side='left')
                _spin(row_a, vars_['ty'], -9999, 9999, 6).pack(side='left', padx=(2, 0))

                # Row B: (indent)   W%:[  ]  H%:[  ]
                row_b = ttk.Frame(pos_lf)
                row_b.grid(row=r+1, column=0, columnspan=2, sticky='w', pady=(1, 2))
                ttk.Label(row_b, text='',
                          width=13).pack(side='left')   # indent to match label above
                ttk.Label(row_b, text='W%:', foreground='#888',
                          font=('Segoe UI', 7)).pack(side='left')
                _spin(row_b, vars_['scx'], 1, 500, 6).pack(side='left', padx=(2, 6))
                ttk.Label(row_b, text='H%:', foreground='#888',
                          font=('Segoe UI', 7)).pack(side='left')
                _spin(row_b, vars_['scy'], 1, 500, 6).pack(side='left', padx=(2, 0))

                r += 2

        _wheel_block(1, 'f')
        _wheel_block(8, 'b')

        # ── Plate corner points ───────────────────────────────────────────────
        plate_lf = ttk.LabelFrame(right, text="Plate Position (Back View)", padding=(8, 4))
        plate_lf.pack(fill='x', pady=(8, 0))

        ttk.Label(plate_lf, text="p1=BL  p2=BR  p3=TR  p4=TL", foreground='#555',
                  font=('Segoe UI', 7)).grid(row=0, column=0, columnspan=4, sticky='w')

        PLATE_COLORS = {'p1': '#ffaa00', 'p2': '#ff44cc', 'p3': '#44ffcc', 'p4': '#aaaaff'}
        for pi, pt in enumerate(('p1','p2','p3','p4')):
            pv = self._pvars.get(pt, {})
            row_fr = ttk.Frame(plate_lf)
            row_fr.grid(row=pi+1, column=0, columnspan=4, sticky='w', pady=(2,0))
            tk.Label(row_fr, text='●', fg=PLATE_COLORS[pt],
                     bg=BG, font=('Segoe UI', 9)).pack(side='left')
            ttk.Label(row_fr, text=pt, font=('Segoe UI', 8), width=3).pack(side='left', padx=(2,6))
            ttk.Label(row_fr, text='X:').pack(side='left')
            tx_dv = pv.get('tx', tk.DoubleVar(value=0))
            ty_dv = pv.get('ty', tk.DoubleVar(value=0))
            _spin(row_fr, tx_dv, -9999, 9999, 6).pack(side='left', padx=(2, 6))
            ttk.Label(row_fr, text='Y:').pack(side='left')
            _spin(row_fr, ty_dv, -9999, 9999, 6).pack(side='left', padx=(2, 0))

        # ── ROW 2: coord readout + Close ─────────────────────────────────────
        foot = ttk.Frame(self, padding=(8, 0, 8, 8))
        foot.grid(row=2, column=0, sticky='ew')
        self._coord_lbl = ttk.Label(
            foot,
            text='Drag coloured circles to move wheels  |  Arrow keys = 1px nudge  |  Shift+Arrow = 10px',
            foreground='#555', font=('Segoe UI', 8))
        self._coord_lbl.pack(side='left')
        ttk.Button(foot, text='Close', command=self.destroy).pack(side='right')
        ttk.Button(foot, text='Reset Positions',
                   command=self._reset_positions).pack(side='right', padx=(0, 6))

    # ── Overlay loading ────────────────────────────────────────────────────────

    def _load_overlays(self):
        if self._loading:
            return
        self._loading = True
        # Read all Tk variables on the main thread before handing off
        view = self._view.get()
        tid  = self._tire_id.get()
        wid  = self._wheel_id.get()
        self._ov_status.set("Extracting images via FFDec…")
        threading.Thread(target=self._load_worker,
                         args=(view, tid, wid), daemon=True).start()

    def _load_worker(self, view: str, tid: int, wid: int):
        vu   = 'F' if view == 'f' else 'B'
        wdir = os.path.join(CACHE_DIR, "car", "wheel")
        loaded, missing = [], []

        def _extract(fname, out_key):
            fpath = os.path.join(wdir, fname)
            if not os.path.exists(fpath):
                missing.append(fname)
                return None
            out = os.path.join(self._tmp_dir, f"ov_{out_key}")
            os.makedirs(out, exist_ok=True)
            try:
                img_path = export_image(fpath, out)
                if img_path:
                    return Image.open(img_path).convert('RGBA')
                missing.append(f"{fname}(no img)")
            except Exception as e:
                missing.append(f"{fname}({e})")
            return None

        try:
            # Front and rear tires/wheels
            for tire_pos in ('F', 'R'):
                for layer, fname in [
                    ('tire',  f'tire{vu}{tire_pos}_{tid}.swf'),
                    ('wheel', f'wheel{vu}{tire_pos}_{wid}.swf'),
                ]:
                    img = _extract(fname, f'{vu}{layer[0]}{tire_pos}')
                    if img:
                        self._overlays[(view, layer, tire_pos)] = img
                        loaded.append(fname)

            # Back-side race tire (back view only)
            if view == 'b':
                img = _extract('tireBack.swf', 'BtireBack')
                if img:
                    self._overlays[(view, 'tire', 'Back')] = img
                    loaded.append('tireBack.swf')
                img = _extract(f'wheelR_{wid}.swf', f'BwheelBack{wid}')
                if img:
                    self._overlays[(view, 'wheel', 'Back')] = img
                    loaded.append(f'wheelR_{wid}.swf')

            parts = []
            if loaded:  parts.append(f"Loaded: {', '.join(loaded)}")
            if missing: parts.append(f"Missing: {', '.join(missing)}")
            status = '  '.join(parts) or 'Done'
        except Exception as e:
            status = f"Error: {e}"
        finally:
            self._loading = False
            self.after(0, lambda s=status: self._ov_status.set(s))
            self.after(0, self._render)

    # ── Rendering ─────────────────────────────────────────────────────────────

    # SWFs that carry position data, not visuals — skip when compositing
    _SKIP_LABELS  = {'tireF', 'tireR', 'wheelMaskAddF', 'wheelMaskAddR', 'decalLoader'}
    # Layer names that sit behind tires (shadow, undercarriage)
    _BG_LAYER_NAMES = ('shadow', 'undercarriage')
    # Correct front-to-back draw order for foreground layers
    _FG_ORDER = ['undercarriage', 'bumperrear', 'bumper', 'body',
                 'line', 'hood', 'roofeffect', 'roof', 'spoiler']

    def _get_split_composite(self):
        """Return (bg_img, fg_img) composited at STAGE_W×STAGE_H.
        bg = shadow/undercarriage (draws behind tires).
        fg = everything else (draws in front of tires)."""
        view     = self._view.get()
        view_tag = f"[{view.upper()}]"
        size     = (self.STAGE_W, self.STAGE_H)
        bg = Image.new('RGBA', size, (0, 0, 0, 0))
        fg = Image.new('RGBA', size, (0, 0, 0, 0))
        found = False

        # One representative slot per SWF (first encountered)
        seen: dict[str, object] = {}
        for s in self._slots:
            if view_tag in s.label and s.swf_path not in seen:
                if not any(sk in s.label for sk in self._SKIP_LABELS):
                    seen[s.swf_path] = s

        def _layer_key(swf_path):
            name = os.path.basename(swf_path).lower().replace('.swf', '')
            for i, k in enumerate(self._FG_ORDER):
                if k in name:
                    return i
            return 4

        for swf_path, slot in sorted(seen.items(), key=lambda kv: _layer_key(kv[0])):
            try:
                img = slot.final_image()
                ox = oy = 0
                if os.path.exists(swf_path):
                    xmin, ymin, w, h = swf_rect_origin(swf_path)
                    ox, oy = int(xmin), int(ymin)
                    tw, th = max(1, int(w)), max(1, int(h))
                    if tw > 0 and th > 0 and (img.width != tw or img.height != th):
                        img = img.resize((tw, th), Image.LANCZOS)
                fname = os.path.basename(swf_path).lower()
                target = bg if any(k in fname for k in self._BG_LAYER_NAMES) else fg
                target.paste(img, (ox, oy), img)
                found = True
            except Exception:
                pass

        return (bg, fg) if found else (None, None)

    def _on_view_change(self):
        view = self._view.get()
        self._render()
        # Auto-load overlays for this view if none have been loaded yet
        if not any(k[0] == view for k in self._overlays):
            self._load_overlays()

    def _render(self, *_):
        self._cv.delete('all')
        self._cids   = {}
        self._tk_ovls.clear()
        view = self._view.get()
        cs   = self.CANVAS_SCALE
        sw   = int(self.STAGE_W * cs)
        sh   = int(self.STAGE_H * cs)

        bg_img, fg_img = self._get_split_composite()

        # 1. Shadow / undercarriage (behind everything)
        if bg_img:
            self._tk_bg = ImageTk.PhotoImage(bg_img.resize((sw, sh), Image.LANCZOS))
            self._cv.create_image(0, 0, anchor='nw', image=self._tk_bg)

        # 2. Tire and wheel overlays (in front of shadow, behind car body)
        tire_positions = ['F', 'R'] + (['Back'] if view == 'b' else [])
        for layer in ('tire', 'wheel'):
            show_layer = self._show_tire if layer == 'tire' else self._show_wheel
            if not show_layer.get():
                continue
            for tire_pos in tire_positions:
                if not self._show_pos[tire_pos].get():
                    continue
                ov_key = (view, layer, tire_pos)
                if ov_key not in self._overlays:
                    continue
                img  = self._overlays[ov_key]
                wkey = (view, tire_pos)
                if wkey not in self._wvars:
                    continue
                scx = self._wvars[wkey]['scx'].get() / 100.0
                scy = self._wvars[wkey]['scy'].get() / 100.0
                dw  = max(1, int(img.width  * scx * cs))
                dh  = max(1, int(img.height * scy * cs))
                tx  = int(self._wvars[wkey]['tx'].get() * cs)
                ty  = int(self._wvars[wkey]['ty'].get() * cs)
                tkimg = ImageTk.PhotoImage(img.resize((dw, dh), Image.LANCZOS))
                self._tk_ovls.append(tkimg)
                self._cv.create_image(tx, ty, anchor='nw', image=tkimg)

        # 3. Car body / bumpers / roof (in front of tires)
        if fg_img:
            self._tk_img = ImageTk.PhotoImage(fg_img.resize((sw, sh), Image.LANCZOS))
            self._cv.create_image(0, 0, anchor='nw', image=self._tk_img)
        elif not bg_img:
            self._cv.create_text(sw // 2, sh // 2, text='Load a car first',
                                  fill='#444', font=('Segoe UI', 12))

        # 4. Plate quad (back view only) — outline + draggable corner handles
        if view == 'b' and self._pvars:
            PLATE_COLORS = {'p1': '#ffaa00', 'p2': '#ff44cc', 'p3': '#44ffcc', 'p4': '#aaaaff'}
            pts_canvas = []
            for pt in ('p1', 'p2', 'p3', 'p4'):
                pv = self._pvars.get(pt, {})
                tx = pv.get('tx', tk.DoubleVar(value=0)).get() * cs
                ty = pv.get('ty', tk.DoubleVar(value=0)).get() * cs
                pts_canvas.append((tx, ty))
            # Draw quad outline (p1-p2-p3-p4 loop)
            for i in range(4):
                x0, y0 = pts_canvas[i]
                x1, y1 = pts_canvas[(i+1) % 4]
                self._cv.create_line(x0, y0, x1, y1, fill='#ffff00', width=1, dash=(4, 3))
            # Draw corner handles
            r = 7
            for pt, (cx, cy) in zip(('p1','p2','p3','p4'), pts_canvas):
                col = PLATE_COLORS[pt]
                self._cv.create_oval(cx-r, cy-r, cx+r, cy+r,
                                      outline=col, fill='', width=2)
                self._cv.create_text(cx, cy, text=pt, fill=col,
                                      font=('Segoe UI', 6))

        # 3. Draggable circles — only for visible positions
        tires_for_view = ['F', 'R'] + (['Back'] if view == 'b' else [])
        for tire in tires_for_view:
            if not self._show_pos[tire].get():
                continue
            key = (view, tire)
            if key not in self._wvars:
                continue
            tx  = int(self._wvars[key]['tx'].get() * cs)
            ty  = int(self._wvars[key]['ty'].get() * cs)
            col = self.TIRE_COLORS[tire]
            r   = self.HANDLE_R
            lbl = tire if tire != 'Back' else 'BK'
            oid = self._cv.create_oval(tx-r, ty-r, tx+r, ty+r,
                                        fill=col, outline='white', width=2, stipple='gray50')
            tid = self._cv.create_text(tx, ty, text=lbl, fill='white',
                                        font=('Segoe UI', 8, 'bold'))
            self._cids[tire] = (oid, tid)

    # ── Drag interaction ──────────────────────────────────────────────────────

    def _hit_tire(self, x, y):
        cs    = self.CANVAS_SCALE
        view  = self._view.get()
        tires = ['F', 'R'] + (['Back'] if view == 'b' else [])
        for tire in tires:
            if not self._show_pos[tire].get():
                continue
            key = (view, tire)
            if key not in self._wvars:
                continue
            # Compare in canvas space (game coords × cs)
            cx = self._wvars[key]['tx'].get() * cs
            cy = self._wvars[key]['ty'].get() * cs
            if (x - cx)**2 + (y - cy)**2 <= self.HANDLE_HIT**2:
                return tire
        return None

    def _on_press(self, evt):
        self._cv.focus_set()
        tire = self._hit_tire(evt.x, evt.y)
        if tire:
            self._drag = tire
            self._cv.config(cursor='fleur')

    def _nudge(self, dx, dy):
        """Arrow-key nudge selected wheel by 1px (or 10px with Shift)."""
        view = self._view.get()
        tires = ['F', 'R'] + (['Back'] if view == 'b' else [])
        for tire in tires:
            if self._show_pos[tire].get():
                key = (view, tire)
                if key in self._wvars:
                    self._wvars[key]['tx'].set(round(self._wvars[key]['tx'].get() + dx))
                    self._wvars[key]['ty'].set(round(self._wvars[key]['ty'].get() + dy))
                    self._coord_lbl.config(
                        text=f"{tire}: x={round(self._wvars[key]['tx'].get())}  "
                             f"y={round(self._wvars[key]['ty'].get())}")
                break
        self._render()

    def _on_drag(self, evt):
        if not self._drag:
            return
        cs   = self.CANVAS_SCALE
        view = self._view.get()
        # Convert canvas px → game coords, clamp to stage bounds
        gx = max(0, min(self.STAGE_W, evt.x / cs))
        gy = max(0, min(self.STAGE_H, evt.y / cs))
        key = (view, self._drag)
        self._wvars[key]['tx'].set(round(gx))
        self._wvars[key]['ty'].set(round(gy))
        # Move circle in canvas space
        cx, cy = gx * cs, gy * cs
        oid, tid = self._cids[self._drag]
        r = self.HANDLE_R
        self._cv.coords(oid, cx-r, cy-r, cx+r, cy+r)
        self._cv.coords(tid, cx, cy)
        self._coord_lbl.config(text=f"{self._drag}: x={round(gx)}  y={round(gy)}")

    def _on_release(self, evt):
        self._drag = None
        self._cv.config(cursor='crosshair')
        self._render()

    def _reset_positions(self):
        for key, vals in self._wsrc.items():
            for vn, dv in self._wvars[key].items():
                dv.set(vals.get(vn, 100 if vn in ('scx', 'scy') else 0))
        for pt, vals in self._psrc.items():
            for vn, dv in self._pvars.get(pt, {}).items():
                if vn in vals:
                    dv.set(round(float(vals[vn]), 2))
        self._render()


# ── Overlay alignment window ───────────────────────────────────────────────────

class OverlayWindow(tk.Toplevel):
    """Overlay alignment tool — sliders, text entries, and draggable corners."""

    MAX_W, MAX_H   = 1200, 700
    HANDLE_R       = 6     # handle circle radius (px)
    HANDLE_HIT     = 14    # grab detection radius (px)
    CORNER_COLORS  = ["#ff4444", "#ffaa00", "#00ff88", "#00aaff"]   # TL TR BR BL
    CORNER_LABELS  = ["TL", "TR", "BR", "BL"]

    def __init__(self, parent, orig_img: Image.Image, new_img: Image.Image,
                 on_accept, on_reject):
        super().__init__(parent, bg=BG)
        self.title("Overlay Alignment Tool")
        self.resizable(True, True)
        self._on_accept = on_accept
        self._on_reject = on_reject
        self._tk_img         = None
        self._render_pending = False
        self._drag_idx       = None   # index of corner being dragged (0-3)
        self._corner_pts     = []     # 4 (x, y) in canvas display coords
        self._canvas_x_off   = 0     # canvas x-offset for side-by-side mode

        self._orig_full = orig_img.convert("RGBA")
        self._new_full  = new_img.convert("RGBA")

        dscale = min(1.0,
                     self.MAX_W / max(orig_img.width,  1),
                     self.MAX_H / max(orig_img.height, 1))
        self._dscale = dscale
        self._DW = max(int(orig_img.width  * dscale), 1)
        self._DH = max(int(orig_img.height * dscale), 1)

        self._orig_d = self._orig_full.resize((self._DW, self._DH), Image.LANCZOS)
        self._new_d  = self._new_full.resize( (self._DW, self._DH), Image.LANCZOS)

        self._build()
        self.after(60, self._render)
        self.grab_set()

    # ── Widget factory helpers ─────────────────────────────────────────────────

    def _lbl(self, parent, text):
        return tk.Label(parent, text=text, bg=BG, fg="#aaa",
                         font=("Segoe UI", 8), anchor="w")

    def _paired(self, parent, label, var, from_, to, res,
                fmt="{:.3f}", row=0, slen=110):
        """Slider + synced entry box on grid row `row`, columns 0-2."""
        self._lbl(parent, label).grid(row=row, column=0, sticky="w", padx=(0, 3))

        sl = tk.Scale(parent, variable=var, from_=from_, to=to, resolution=res,
                       orient="horizontal", length=slen, bg=BG, fg=FG,
                       troughcolor=DARK, highlightthickness=0, relief="flat",
                       showvalue=0, activebackground=ACC,
                       command=self._on_ctrl_change)
        sl.grid(row=row, column=1, padx=(0, 3))

        ent = tk.Entry(parent, width=7, bg="#16213e", fg=ACC,
                        insertbackground=FG, font=("Consolas", 8),
                        relief="flat", highlightthickness=1,
                        highlightbackground="#333", highlightcolor=ACC)
        ent.insert(0, fmt.format(var.get()))
        ent.grid(row=row, column=2, padx=(0, 6))

        # Slider → entry  (one-way trace, avoids feedback loops)
        def _to_ent(*_):
            v = fmt.format(var.get())
            if ent.get() != v:
                ent.delete(0, tk.END)
                ent.insert(0, v)
        var.trace_add("write", _to_ent)

        # Entry → slider  (only on commit)
        def _from_ent(evt=None):
            try:
                v = float(ent.get())
                v = max(from_, min(to, v))
                # snap to slider resolution to keep them in sync
                snapped = round(v / res) * res if res else v
                var.set(round(snapped, 10))   # avoid fp noise in display
                self._on_ctrl_change()
            except ValueError:
                pass
        ent.bind("<Return>",   _from_ent)
        ent.bind("<FocusOut>", _from_ent)
        # Also update on Tab so keyboard users can tab through fields
        ent.bind("<Tab>", lambda e: (self.focus_set(), _from_ent()))

        return sl, ent

    def _spinbox_int(self, parent, var, from_, to, width=6, **grid_kw):
        sb = tk.Spinbox(parent, textvariable=var, from_=from_, to=to, width=width,
                         bg="#16213e", fg=ACC, buttonbackground="#0f3460",
                         relief="flat", font=("Consolas", 8),
                         command=self._on_ctrl_change)
        sb.bind("<Return>",   self._on_ctrl_change)
        sb.bind("<FocusOut>", self._on_ctrl_change)
        sb.grid(**grid_kw)
        return sb

    # ── Build UI ───────────────────────────────────────────────────────────────

    def _build(self):
        tk.Label(self,
                  text="Use sliders or type exact values. "
                       "Drag the coloured corner handles on the canvas to reshape. "
                       "Accept bakes the transform at full resolution.",
                  bg=BG, fg="#aaa", font=("Segoe UI", 9), wraplength=980
                  ).pack(fill="x", padx=12, pady=(8, 4))

        ctrl = tk.Frame(self, bg=BG)
        ctrl.pack(fill="x", padx=12, pady=2)

        # ── Opacity ───────────────────────────────────────────────────────────
        g1 = tk.LabelFrame(ctrl, text="Opacity", bg=BG, fg=ACC,
                             font=("Segoe UI", 8, "bold"), padx=6, pady=4)
        g1.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        self._orig_op = tk.DoubleVar(value=0.45)
        self._new_op  = tk.DoubleVar(value=0.85)
        self._paired(g1, "Original",  self._orig_op, 0, 1, 0.01, "{:.2f}", row=0)
        self._paired(g1, "New image", self._new_op,  0, 1, 0.01, "{:.2f}", row=1)

        # ── Position ──────────────────────────────────────────────────────────
        g2 = tk.LabelFrame(ctrl, text="Position (px)", bg=BG, fg=ACC,
                             font=("Segoe UI", 8, "bold"), padx=6, pady=4)
        g2.grid(row=0, column=1, sticky="nsew", padx=(0, 6))

        self._nx = tk.IntVar(value=0)
        self._ny = tk.IntVar(value=0)

        self._lbl(g2, "X offset").grid(row=0, column=0, sticky="w")
        self._spinbox_int(g2, self._nx, -4000, 4000, row=0, column=1)
        self._lbl(g2, "Y offset").grid(row=1, column=0, sticky="w")
        self._spinbox_int(g2, self._ny, -4000, 4000, row=1, column=1)

        # Fine-nudge sliders (accumulate into spinbox — spring back to 0)
        self._lbl(g2, "Fine X").grid(row=0, column=2, sticky="w", padx=(8, 0))
        self._fine_x = tk.IntVar(value=0)
        tk.Scale(g2, variable=self._fine_x, from_=-30, to=30, resolution=1,
                  orient="horizontal", length=80, bg=BG, fg=FG, troughcolor=DARK,
                  highlightthickness=0, relief="flat", showvalue=0,
                  activebackground=ACC,
                  command=self._on_ctrl_change).grid(row=0, column=3, padx=(0,4))
        self._fine_x.trace_add("write", self._on_fine_x)

        self._lbl(g2, "Fine Y").grid(row=1, column=2, sticky="w", padx=(8, 0))
        self._fine_y = tk.IntVar(value=0)
        tk.Scale(g2, variable=self._fine_y, from_=-30, to=30, resolution=1,
                  orient="horizontal", length=80, bg=BG, fg=FG, troughcolor=DARK,
                  highlightthickness=0, relief="flat", showvalue=0,
                  activebackground=ACC,
                  command=self._on_ctrl_change).grid(row=1, column=3, padx=(0,4))
        self._fine_y.trace_add("write", self._on_fine_y)

        # ── Scale / Stretch ───────────────────────────────────────────────────
        g3 = tk.LabelFrame(ctrl, text="Scale / Stretch", bg=BG, fg=ACC,
                             font=("Segoe UI", 8, "bold"), padx=6, pady=4)
        g3.grid(row=0, column=2, sticky="nsew", padx=(0, 6))

        self._scale     = tk.DoubleVar(value=1.0)
        self._stretch_x = tk.DoubleVar(value=1.0)
        self._stretch_y = tk.DoubleVar(value=1.0)

        self._paired(g3, "Scale",      self._scale,     0.05, 5.0,  0.005, "{:.3f}", row=0)
        self._paired(g3, "Stretch X",  self._stretch_x, 0.1,  4.0,  0.005, "{:.3f}", row=1)
        self._paired(g3, "Stretch Y",  self._stretch_y, 0.1,  4.0,  0.005, "{:.3f}", row=2)
        ttk.Button(g3, text="Reset scale",
                    command=self._reset_scale).grid(row=3, column=0, columnspan=3,
                                                     sticky="ew", pady=(4, 0))

        # ── Skew ──────────────────────────────────────────────────────────────
        g4 = tk.LabelFrame(ctrl, text="Skew (°)", bg=BG, fg=ACC,
                             font=("Segoe UI", 8, "bold"), padx=6, pady=4)
        g4.grid(row=0, column=3, sticky="nsew", padx=(0, 6))

        self._skew_x = tk.DoubleVar(value=0.0)
        self._skew_y = tk.DoubleVar(value=0.0)

        self._paired(g4, "Skew X →", self._skew_x, -60, 60, 0.5, "{:.1f}", row=0)
        self._paired(g4, "Skew Y ↓", self._skew_y, -60, 60, 0.5, "{:.1f}", row=1)
        ttk.Button(g4, text="Reset skew",
                    command=self._reset_skew).grid(row=2, column=0, columnspan=3,
                                                    sticky="ew", pady=(4, 0))

        # ── Rotate / Flip ─────────────────────────────────────────────────────
        g_rot = tk.LabelFrame(ctrl, text="Rotate / Flip", bg=BG, fg=ACC,
                               font=("Segoe UI", 8, "bold"), padx=6, pady=4)
        g_rot.grid(row=0, column=4, sticky="nsew", padx=(0, 6))

        self._rotate = tk.DoubleVar(value=0.0)
        self._flip_h = tk.BooleanVar(value=False)
        self._flip_v = tk.BooleanVar(value=False)

        self._paired(g_rot, "Rotate °", self._rotate, -180, 180, 0.1, "{:.2f}", row=0, slen=100)
        self._fine_rot = tk.DoubleVar(value=0.0)
        self._paired(g_rot, "Fine °",   self._fine_rot, -2, 2, 0.01, "{:.2f}", row=1, slen=100)
        self._fine_rot.trace_add("write", self._on_fine_rot)

        flip_fr = tk.Frame(g_rot, bg=BG)
        flip_fr.grid(row=2, column=0, columnspan=3, sticky="w", pady=(4, 0))
        tk.Checkbutton(flip_fr, text="Flip H", variable=self._flip_h,
                        bg=BG, fg=FG, selectcolor="#0f3460", activebackground=BG,
                        command=self._on_ctrl_change).pack(side="left", padx=(0, 6))
        tk.Checkbutton(flip_fr, text="Flip V", variable=self._flip_v,
                        bg=BG, fg=FG, selectcolor="#0f3460", activebackground=BG,
                        command=self._on_ctrl_change).pack(side="left")

        ttk.Button(g_rot, text="Reset rotate",
                    command=self._reset_rotate).grid(row=3, column=0, columnspan=3,
                                                     sticky="ew", pady=(4, 0))

        # ── View mode ─────────────────────────────────────────────────────────
        g5 = tk.LabelFrame(ctrl, text="View", bg=BG, fg=ACC,
                             font=("Segoe UI", 8, "bold"), padx=6, pady=4)
        g5.grid(row=0, column=5, sticky="nsew")

        self._mode = tk.StringVar(value="overlay")
        for val, txt in [("overlay", "Overlay"),
                          ("side",   "Side by side"),
                          ("diff",   "Difference")]:
            tk.Radiobutton(g5, text=txt, variable=self._mode, value=val,
                            bg=BG, fg=FG, selectcolor="#0f3460",
                            activebackground=BG,
                            command=self._render).pack(anchor="w")

        ttk.Button(g5, text="Reset ALL",
                    command=self._reset_all).pack(fill="x", pady=(6, 0))

        # ── Transform readout ─────────────────────────────────────────────────
        self._xform_lbl = tk.Label(self, text="", bg=BG, fg="#555",
                                    font=("Consolas", 7))
        self._xform_lbl.pack(anchor="w", padx=14)

        # ── Canvas ────────────────────────────────────────────────────────────
        self._canvas = tk.Canvas(self, width=self._DW, height=self._DH,
                                   bg=DARK, cursor="crosshair",
                                   highlightthickness=1, highlightbackground="#333")
        self._canvas.pack(padx=12, pady=6, fill="both", expand=True)

        self._canvas.bind("<ButtonPress-1>",   self._on_canvas_press)
        self._canvas.bind("<B1-Motion>",        self._on_canvas_drag)
        self._canvas.bind("<ButtonRelease-1>", self._on_canvas_release)

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_row = tk.Frame(self, bg=BG)
        btn_row.pack(pady=(0, 10))

        tk.Button(btn_row, text="✓  Accept — bake and use",
                   bg=ACC, fg=DARK, font=("Segoe UI", 10, "bold"),
                   relief="flat", padx=16, pady=6,
                   command=self._accept).pack(side="left", padx=8)

        tk.Button(btn_row, text="✗  Reject — discard",
                   bg="#333", fg=FG, font=("Segoe UI", 10),
                   relief="flat", padx=16, pady=6,
                   command=self._reject).pack(side="left", padx=8)

    # ── Fine-nudge accumulators ────────────────────────────────────────────────

    def _on_fine_x(self, *_):
        d = self._fine_x.get()
        if d != 0:
            self._nx.set(self._nx.get() + d)
            self._fine_x.set(0)

    def _on_fine_y(self, *_):
        d = self._fine_y.get()
        if d != 0:
            self._ny.set(self._ny.get() + d)
            self._fine_y.set(0)

    def _on_fine_rot(self, *_):
        d = self._fine_rot.get()
        if d != 0:
            new_val = max(-180, min(180, round(self._rotate.get() + d, 2)))
            self._rotate.set(new_val)
            self._fine_rot.set(0)

    # ── Reset helpers ──────────────────────────────────────────────────────────

    def _reset_scale(self):
        self._scale.set(1.0); self._stretch_x.set(1.0); self._stretch_y.set(1.0)
        self._render()

    def _reset_skew(self):
        self._skew_x.set(0.0); self._skew_y.set(0.0)
        self._render()

    def _reset_rotate(self):
        self._rotate.set(0.0); self._flip_h.set(False); self._flip_v.set(False)
        self._render()

    def _reset_all(self):
        self._nx.set(0); self._ny.set(0)
        self._reset_scale(); self._reset_skew(); self._reset_rotate()

    # ── Affine math ────────────────────────────────────────────────────────────

    def _fwd_matrix(self, W: int, H: int, *, display_nudge=False) -> np.ndarray:
        """
        Build the 3×3 forward affine matrix (image-space → canvas-space).
        With display_nudge=True the nudge is in display pixels (used for
        handle computation and corner fitting); otherwise it is scaled to
        the given W×H full-resolution space.
        """
        cx, cy = W / 2.0, H / 2.0
        sx = max(self._scale.get() * self._stretch_x.get(), 1e-6)
        sy = max(self._scale.get() * self._stretch_y.get(), 1e-6)
        kx = math.tan(math.radians(self._skew_x.get()))
        ky = math.tan(math.radians(self._skew_y.get()))
        if display_nudge:
            nx, ny = float(self._nx.get()), float(self._ny.get())
        else:
            ds = W / self._DW
            nx, ny = self._nx.get() * ds, self._ny.get() * ds

        theta  = math.radians(self._rotate.get())
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        fh = -1.0 if self._flip_h.get() else 1.0
        fv = -1.0 if self._flip_v.get() else 1.0

        T_to   = np.array([[1, 0, -cx],   [0, 1, -cy],   [0, 0, 1]], float)
        M_x    = np.array([[sx * fh, kx, 0], [ky, sy * fv, 0], [0, 0, 1]], float)
        R      = np.array([[cos_t, -sin_t, 0], [sin_t, cos_t, 0], [0, 0, 1]], float)
        T_from = np.array([[1, 0, cx+nx], [0, 1, cy+ny], [0, 0, 1]], float)
        return T_from @ R @ M_x @ T_to

    def _affine_pil(self, W: int, H: int) -> tuple:
        """PIL AFFINE 6-tuple (inverse map dst→src) for an image of size W×H."""
        M_inv = np.linalg.inv(self._fwd_matrix(W, H))
        return (M_inv[0,0], M_inv[0,1], M_inv[0,2],
                M_inv[1,0], M_inv[1,1], M_inv[1,2])

    def _transform_image(self, img: Image.Image, W: int, H: int) -> Image.Image:
        return img.transform((W, H), Image.AFFINE, self._affine_pil(W, H),
                              resample=Image.BILINEAR, fillcolor=(0, 0, 0, 0))

    def _set_alpha(self, img: Image.Image, opacity: float) -> Image.Image:
        arr = np.array(img, dtype=np.float32)
        arr[..., 3] = np.clip(arr[..., 3] * opacity, 0, 255)
        return Image.fromarray(arr.astype(np.uint8), "RGBA")

    # ── Corner handle geometry ─────────────────────────────────────────────────

    def _compute_corners(self) -> list:
        """Return the 4 image corners mapped through the forward display transform."""
        DW, DH = self._DW, self._DH
        M = self._fwd_matrix(DW, DH, display_nudge=True)
        pts = []
        for x, y in [(0,0), (DW,0), (DW,DH), (0,DH)]:
            v = M @ np.array([x, y, 1.0])
            pts.append((float(v[0]), float(v[1])))
        return pts

    def _draw_handles(self):
        self._canvas.delete("handle")
        for i, (x, y) in enumerate(self._corner_pts):
            cx = x + self._canvas_x_off
            r  = self.HANDLE_R
            col = self.CORNER_COLORS[i]
            # Filled circle
            self._canvas.create_oval(cx-r, y-r, cx+r, y+r,
                                      outline="white", fill=col, width=2,
                                      tags=("handle", f"h{i}"))
            # Edge lines from corner to nearby corners (outline the quad)
            next_i = (i + 1) % 4
            nx2, ny2 = self._corner_pts[next_i]
            self._canvas.create_line(cx, y,
                                      nx2 + self._canvas_x_off, ny2,
                                      fill=col, width=1, dash=(4, 3),
                                      tags=("handle",))
            # Label
            self._canvas.create_text(cx + r + 2, y - r - 2,
                                      text=self.CORNER_LABELS[i],
                                      fill=col, font=("Consolas", 7),
                                      anchor="sw", tags=("handle",))

    # ── Canvas drag ────────────────────────────────────────────────────────────

    def _on_canvas_press(self, event):
        self._drag_idx = None
        for i, (x, y) in enumerate(self._corner_pts):
            cx = x + self._canvas_x_off
            if abs(event.x - cx) <= self.HANDLE_HIT and \
               abs(event.y - y)  <= self.HANDLE_HIT:
                self._drag_idx = i
                self._canvas.configure(cursor="fleur")
                break

    def _on_canvas_drag(self, event):
        if self._drag_idx is None:
            return
        pts = list(self._corner_pts)
        pts[self._drag_idx] = (event.x - self._canvas_x_off, event.y)
        self._fit_from_corners(pts)

    def _on_canvas_release(self, event):
        self._drag_idx = None
        self._canvas.configure(cursor="crosshair")

    def _fit_from_corners(self, new_pts: list):
        """
        Fit a forward affine (least-squares over 4 pts) from the new corner
        positions and decompose it back into scale/stretch/skew/nudge controls.
        """
        DW, DH = self._DW, self._DH
        src = np.array([(0,0),(DW,0),(DW,DH),(0,DH)], float)
        dst = np.array(new_pts, float)

        # Build overdetermined system:  M_fwd maps [x y 1]^T → [x' y' 1]^T
        A  = np.zeros((8, 6))
        bv = np.zeros(8)
        for i in range(4):
            x, y   = src[i]
            xp, yp = dst[i]
            A[2*i]   = [x, y, 1, 0, 0, 0]
            A[2*i+1] = [0, 0, 0, x, y, 1]
            bv[2*i],  bv[2*i+1] = xp, yp

        params, *_ = np.linalg.lstsq(A, bv, rcond=None)
        a, b_c, c, d, e, f = params

        # The 2×2 linear part equals our [[sx, kx],[ky, sy]] block
        sx = float(np.clip(a,   0.02, 20.0))
        sy = float(np.clip(e,   0.02, 20.0))
        kx = float(np.clip(b_c, -10,  10))
        ky = float(np.clip(d,   -10,  10))

        scale = math.sqrt(sx * sy)
        if scale < 1e-4:
            scale = 1e-4

        stretch_x  = sx / scale
        stretch_y  = sy / scale
        skew_x_deg = math.degrees(math.atan(kx))
        skew_y_deg = math.degrees(math.atan(ky))

        # Recover nudge from translation coefficients
        # c = -sx*cx - kx*cy + cx + nx  → nx = c - cx + sx*cx + kx*cy
        cx_d, cy_d = DW / 2.0, DH / 2.0
        nx_f = float(c) - cx_d + sx * cx_d + kx * cy_d
        ny_f = float(f) - cy_d + ky * cx_d + sy * cy_d

        # Batch-update all controls without triggering mid-set renders
        self._render_pending = True
        self._scale.set(    round(float(np.clip(scale,     0.05, 5.0)),  4))
        self._stretch_x.set(round(float(np.clip(stretch_x, 0.1,  4.0)), 4))
        self._stretch_y.set(round(float(np.clip(stretch_y, 0.1,  4.0)), 4))
        self._skew_x.set(   round(float(np.clip(skew_x_deg, -60, 60)),  2))
        self._skew_y.set(   round(float(np.clip(skew_y_deg, -60, 60)),  2))
        self._nx.set(int(round(float(np.clip(nx_f, -4000, 4000)))))
        self._ny.set(int(round(float(np.clip(ny_f, -4000, 4000)))))
        self._render_pending = False
        self._do_render()

    # ── Render ─────────────────────────────────────────────────────────────────

    def _on_ctrl_change(self, *_):
        if not self._render_pending:
            self._render_pending = True
            self.after(30, self._do_render)

    def _render(self, *_):
        self._on_ctrl_change()

    def _do_render(self):
        self._render_pending = False
        try:
            mode = self._mode.get()
            W, H = self._DW, self._DH

            new_xf = self._transform_image(self._new_d, W, H)

            if mode == "side":
                combined = Image.new("RGBA", (W*2, H), (25, 25, 45, 255))
                combined.paste(self._orig_d, (0, 0))
                combined.paste(new_xf, (W, 0), new_xf)
                draw = ImageDraw.Draw(combined)
                draw.line([(W,0),(W,H)], fill=ACC, width=2)
                draw.text((6,   4), "ORIGINAL",  fill="#888")
                draw.text((W+6, 4), "NEW IMAGE", fill="#888")
                result = combined.convert("RGB")
                self._canvas_x_off = W

            elif mode == "diff":
                oa = np.array(self._orig_d, dtype=np.float32)[..., :3]
                na = np.array(new_xf,       dtype=np.float32)[..., :3]
                diff = np.abs(oa - na).mean(axis=2)
                mx   = diff.max()
                norm = (diff / mx * 255).astype(np.uint8) if mx > 0 \
                       else np.zeros((H, W), np.uint8)
                rgb = np.zeros((H, W, 3), np.uint8)
                rgb[..., 0] = norm
                rgb[..., 1] = 255 - norm
                result = Image.fromarray(rgb, "RGB")
                self._canvas_x_off = 0

            else:   # overlay
                bg = Image.new("RGBA", (W, H), (25, 25, 45, 255))
                d  = ImageDraw.Draw(bg)
                cs = 12
                for gy in range(0, H, cs):
                    for gx in range(0, W, cs):
                        if (gx//cs + gy//cs) % 2 == 0:
                            d.rectangle([gx, gy, gx+cs-1, gy+cs-1], fill=(35,35,60))

                result = Image.alpha_composite(bg, self._set_alpha(self._orig_d, self._orig_op.get()))
                result = Image.alpha_composite(result, self._set_alpha(new_xf, self._new_op.get()))

                d2 = ImageDraw.Draw(result)
                d2.line([(W//2,0),(W//2,H)], fill=(80,80,120,100), width=1)
                d2.line([(0,H//2),(W,H//2)], fill=(80,80,120,100), width=1)
                self._canvas_x_off = 0

            self._canvas.configure(width=result.width, height=result.height)
            self._tk_img = ImageTk.PhotoImage(result)
            self._canvas.delete("all")
            self._canvas.create_image(0, 0, image=self._tk_img, anchor="nw")

            # Draw corner handles on top of the image
            self._corner_pts = self._compute_corners()
            self._draw_handles()

            # Status readout
            sx = self._scale.get() * self._stretch_x.get()
            sy = self._scale.get() * self._stretch_y.get()
            self._xform_lbl.config(
                text=f"pos ({self._nx.get():+d}, {self._ny.get():+d})  "
                     f"eff-scale X {sx:.3f}  Y {sy:.3f}  "
                     f"skew X {self._skew_x.get():+.1f}°  Y {self._skew_y.get():+.1f}°  "
                     f"— drag coloured corners to reshape")

        except Exception as e:
            import traceback
            self._canvas.delete("all")
            self._canvas.create_text(
                self._DW//2, self._DH//2,
                text=f"Render error:\n{e}\n\n{traceback.format_exc()}",
                fill="#e94560", font=("Consolas", 8), width=self._DW-20)

    # ── Accept / Reject ────────────────────────────────────────────────────────

    def _accept(self):
        W, H = self._orig_full.size
        # The overlay preview always works on _new_d which is _new_full resized
        # to (DW, DH).  To get a consistent bake we resize _new_full to (W, H)
        # first — otherwise the affine (centred on W/2, H/2) only reads a
        # W×H crop of the native-resolution source rather than the full image.
        new_rs = (self._new_full.resize((W, H), Image.LANCZOS)
                  if self._new_full.size != (W, H) else self._new_full)
        coef  = self._affine_pil(W, H)
        baked = new_rs.transform((W, H), Image.AFFINE, coef,
                                  resample=Image.BILINEAR, fillcolor=(0, 0, 0, 0))
        self._on_accept(baked)
        self.destroy()

    def _reject(self):
        self._on_reject()
        self.destroy()


# ── Parts Catalogue Editor ────────────────────────────────────────────────────

class PartsCatalogueDialog(tk.Toplevel):
    """Editor for creating and managing partsCatalogue <p> entries."""

    PART_TYPES = ["engine", "turbo", "intake", "exhaust", "suspension", "tires",
                  "wheels", "brakes", "transmission", "body", "spoiler", "nitrous"]

    FIELDS = [
        ("n",   "Name",          "str"),
        ("t",   "Type",          "combo"),
        ("hp",  "Horsepower",    "int"),
        ("tq",  "Torque",        "int"),
        ("wt",  "Weight",        "int"),
        ("ps",  "Size (ps)",     "int"),
        ("ar",  "Aspect (ar)",   "int"),
        ("l",   "Level",         "int"),
        ("p",   "Price",         "int"),
        ("ai",  "AI rating",     "float"),
        ("pi",  "Player rating", "float"),
        ("ci",  "Car ID",        "int"),
        ("scx", "Scale X",       "float"),
        ("scy", "Scale Y",       "float"),
    ]

    def __init__(self, parent, **kw):
        super().__init__(parent, bg=BG, **kw)
        self.title("Parts Catalogue Editor")
        self.resizable(True, True)
        self.minsize(900, 560)
        self._parts: list[dict] = []
        self._sel_idx: int | None = None
        self._field_vars: dict[str, tk.Variable] = {}
        self._groups: dict[str, list] = {}
        self._icon_tk = None
        self._icon_cache: dict[str, str] = {}   # swf_path -> extracted png path
        self._parts_dir = os.path.join(CACHE_DIR, "parts")
        self._build_ui()
        self._scan_cache()
        self.grab_set()

    def _build_ui(self):
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # Left: parts list
        left = ttk.Frame(self, padding=(8, 8, 4, 8))
        left.grid(row=0, column=0, sticky="nsew")
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)

        ttk.Label(left, text="Parts", foreground=ACC,
                  font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w")

        self._lb = tk.Listbox(left, bg=DARK, fg=FG, selectbackground="#0f3460",
                               width=26, font=("Consolas", 8))
        self._lb.grid(row=1, column=0, sticky="nsew", pady=(4, 4))
        self._lb.bind("<<ListboxSelect>>", self._on_select)

        btn_fr = ttk.Frame(left)
        btn_fr.grid(row=2, column=0, sticky="ew")
        ttk.Button(btn_fr, text="+ New Part", style="Accent.TButton",
                   command=self._new_part).pack(side="left", padx=(0, 4))
        ttk.Button(btn_fr, text="Duplicate",
                   command=self._duplicate).pack(side="left", padx=(0, 4))
        ttk.Button(btn_fr, text="Remove",
                   command=self._remove).pack(side="left")

        # ── Cache icon picker ──────────────────────────────────────────────────
        icon_lf = ttk.LabelFrame(left, text="Cache Icon", padding=6)
        icon_lf.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        icon_lf.columnconfigure(1, weight=1)

        # Preview canvas
        self._icon_cv = tk.Canvas(icon_lf, width=80, height=80,
                                   bg=DARK, highlightthickness=1,
                                   highlightbackground="#333")
        self._icon_cv.grid(row=0, column=0, rowspan=3, padx=(0, 8))
        self._icon_cv.create_text(40, 40, text="no icon", fill="#444",
                                   font=("Segoe UI", 7), tags="placeholder")

        ttk.Label(icon_lf, text="Cat:").grid(row=0, column=1, sticky="w")
        self._icon_cat = tk.StringVar()
        self._icon_cat_cb = ttk.Combobox(icon_lf, textvariable=self._icon_cat,
                                          width=6, state="readonly")
        self._icon_cat_cb.grid(row=0, column=2, sticky="w", padx=(4, 0))
        self._icon_cat_cb.bind("<<ComboboxSelected>>", self._on_cat_change)

        ttk.Label(icon_lf, text="ID:").grid(row=1, column=1, sticky="w", pady=(4,0))
        self._icon_id = tk.IntVar(value=1)
        self._icon_id_cb = ttk.Combobox(icon_lf, textvariable=self._icon_id,
                                          width=6, state="readonly")
        self._icon_id_cb.grid(row=1, column=2, sticky="w", padx=(4, 0), pady=(4,0))

        ttk.Button(icon_lf, text="Load Icon", style="Accent.TButton",
                   command=self._load_icon).grid(row=2, column=1, columnspan=2,
                                                  sticky="ew", pady=(6, 0))
        ttk.Button(icon_lf, text="Attach to Part",
                   command=self._attach_icon).grid(row=3, column=1, columnspan=2,
                                                    sticky="ew", pady=(4, 0))
        self._icon_lbl = ttk.Label(icon_lf, text="", foreground="#666",
                                    font=("Segoe UI", 7), wraplength=110)
        self._icon_lbl.grid(row=4, column=1, columnspan=2, sticky="w", pady=(4, 0))

        # Right: field editor + groups + XML
        right = ttk.Frame(self, padding=(4, 8, 8, 8))
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)

        fields_lf = ttk.LabelFrame(right, text="Part Attributes", padding=8)
        fields_lf.grid(row=0, column=0, sticky="ew")
        fields_lf.columnconfigure(1, weight=1)
        fields_lf.columnconfigure(3, weight=1)

        for i, (key, label, typ) in enumerate(self.FIELDS):
            row_i = i // 2
            col_base = (i % 2) * 2
            ttk.Label(fields_lf, text=f"{label}:").grid(
                row=row_i, column=col_base, sticky="w", padx=(0, 4), pady=2)
            if typ == "combo":
                var = tk.StringVar(value=self.PART_TYPES[0])
                w = ttk.Combobox(fields_lf, textvariable=var,
                                 values=self.PART_TYPES, width=14, state="readonly")
            elif typ == "int":
                var = tk.IntVar(value=0)
                w = tk.Spinbox(fields_lf, textvariable=var, from_=0, to=999999,
                               increment=1, width=8, bg="#16213e", fg=ACC,
                               buttonbackground="#0f3460", relief="flat",
                               font=("Consolas", 9))
            elif typ == "float":
                var = tk.DoubleVar(value=0.0)
                w = tk.Spinbox(fields_lf, textvariable=var, from_=0.0, to=9999.0,
                               increment=0.1, width=8, format="%.2f",
                               bg="#16213e", fg=ACC, buttonbackground="#0f3460",
                               relief="flat", font=("Consolas", 9))
            else:
                var = tk.StringVar()
                w = ttk.Entry(fields_lf, textvariable=var, width=16)
            self._field_vars[key] = var
            w.grid(row=row_i, column=col_base + 1, sticky="ew", padx=(0, 12), pady=2)

        apply_row = ttk.Frame(fields_lf)
        apply_row.grid(row=len(self.FIELDS) // 2 + 1, column=0, columnspan=4,
                       sticky="ew", pady=(8, 0))
        ttk.Button(apply_row, text="Apply to selected part", style="Accent.TButton",
                   command=self._apply_fields).pack(side="left", padx=(0, 8))
        ttk.Button(apply_row, text="Add as new part",
                   command=self._add_from_fields).pack(side="left")

        # Groups
        grp_lf = ttk.LabelFrame(right, text="Part Groups", padding=8)
        grp_lf.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        grp_lf.columnconfigure(0, weight=1)

        grp_row = ttk.Frame(grp_lf)
        grp_row.grid(row=0, column=0, sticky="ew")
        self._grp_name = tk.StringVar()
        ttk.Entry(grp_row, textvariable=self._grp_name, width=18).pack(
            side="left", padx=(0, 4))
        ttk.Button(grp_row, text="Save Group",
                   command=self._save_group).pack(side="left", padx=(0, 8))
        self._grp_combo = ttk.Combobox(grp_row, width=16, state="readonly")
        self._grp_combo.pack(side="left", padx=(0, 4))
        ttk.Button(grp_row, text="Load",
                   command=self._load_group).pack(side="left")

        # XML output
        xml_lf = ttk.LabelFrame(right, text="XML Output", padding=8)
        xml_lf.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        xml_lf.columnconfigure(0, weight=1)

        xml_btn_row = ttk.Frame(xml_lf)
        xml_btn_row.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        ttk.Button(xml_btn_row, text="Generate XML", style="Accent.TButton",
                   command=self._generate_xml).pack(side="left", padx=(0, 8))
        ttk.Button(xml_btn_row, text="Copy to Clipboard",
                   command=self._copy_xml).pack(side="left", padx=(0, 8))
        ttk.Button(xml_btn_row, text="Import from XML",
                   command=self._import_xml).pack(side="left")

        self._xml_out = tk.Text(xml_lf, height=4, bg="#16213e", fg="#00ff88",
                                 insertbackground=FG, font=("Consolas", 8),
                                 relief="flat", wrap="char")
        self._xml_out.grid(row=1, column=0, sticky="ew")

        # ── Build Part SWF ────────────────────────────────────────────────────
        build_lf = ttk.LabelFrame(right, text="Build Part SWF", padding=8)
        build_lf.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        build_lf.columnconfigure(1, weight=1)

        ttk.Label(build_lf, text="Source image:").grid(row=0, column=0, sticky="w")
        self._build_img_var = tk.StringVar()
        ttk.Entry(build_lf, textvariable=self._build_img_var).grid(
            row=0, column=1, sticky="ew", padx=(4, 4))
        ttk.Button(build_lf, text="Browse…",
                   command=self._browse_build_img).grid(row=0, column=2)
        ttk.Button(build_lf, text="Use loaded cache icon",
                   command=self._use_cache_icon_for_build).grid(
                   row=1, column=0, columnspan=3, sticky="w", pady=(4, 0))

        dims_fr = ttk.Frame(build_lf)
        dims_fr.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(6, 0))
        self._bld_sw = tk.IntVar(value=640)
        self._bld_sh = tk.IntVar(value=400)
        self._bld_ox = tk.IntVar(value=0)
        self._bld_oy = tk.IntVar(value=0)
        for col, (lbl, var) in enumerate(
                [("Stage W", self._bld_sw), ("Stage H", self._bld_sh),
                 ("Offset X", self._bld_ox), ("Offset Y", self._bld_oy)]):
            ttk.Label(dims_fr, text=f"{lbl}:").grid(row=0, column=col*2,
                      sticky="w", padx=(0 if col == 0 else 10, 2))
            tk.Spinbox(dims_fr, textvariable=var, from_=-9999, to=9999, width=6,
                       bg="#16213e", fg=ACC, buttonbackground="#0f3460", relief="flat",
                       font=("Consolas", 9)).grid(row=0, column=col*2+1, sticky="w")

        ttk.Label(build_lf, text="Output SWF:").grid(row=3, column=0, sticky="w", pady=(6, 0))
        self._build_out_var = tk.StringVar()
        ttk.Entry(build_lf, textvariable=self._build_out_var).grid(
            row=3, column=1, sticky="ew", padx=(4, 4), pady=(6, 0))
        ttk.Button(build_lf, text="Browse…",
                   command=self._browse_build_out).grid(row=3, column=2, pady=(6, 0))

        ttk.Button(build_lf, text="Build SWF", style="Accent.TButton",
                   command=self._do_build_swf).grid(
                   row=4, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        self._build_status = ttk.Label(build_lf, text="",
                                        foreground="#666", font=("Segoe UI", 8))
        self._build_status.grid(row=5, column=0, columnspan=3, sticky="w", pady=(4, 0))

    # ── Cache icon methods ─────────────────────────────────────────────────────

    def _scan_cache(self):
        """Populate category combobox from cache/parts/ filenames."""
        if not os.path.isdir(self._parts_dir):
            return
        cats = set()
        for f in os.listdir(self._parts_dir):
            if f.endswith(".swf") and "_" in f:
                cats.add(f.split("_")[0])
        cats = sorted(cats, key=lambda x: int(x) if x.isdigit() else 0)
        self._icon_cat_cb['values'] = cats
        if cats:
            self._icon_cat.set(cats[0])
            self._on_cat_change()

    def _on_cat_change(self, *_):
        cat = self._icon_cat.get()
        if not cat or not os.path.isdir(self._parts_dir):
            return
        ids = []
        for f in sorted(os.listdir(self._parts_dir)):
            if f.startswith(f"{cat}_") and f.endswith(".swf"):
                part_id = f[len(cat)+1:-4]
                if part_id.isdigit():
                    ids.append(int(part_id))
        ids.sort()
        self._icon_id_cb['values'] = ids
        if ids:
            self._icon_id.set(ids[0])

    def _load_icon(self):
        cat = self._icon_cat.get()
        pid = self._icon_id.get()
        swf = os.path.join(self._parts_dir, f"{cat}_{pid}.swf")
        if not os.path.exists(swf):
            self._icon_lbl.config(text=f"Not found: {cat}_{pid}.swf")
            return
        self._icon_lbl.config(text="Extracting…")
        self.update_idletasks()
        threading.Thread(target=self._extract_icon, args=(swf,), daemon=True).start()

    def _extract_icon(self, swf: str):
        if swf in self._icon_cache and os.path.exists(self._icon_cache[swf]):
            png = self._icon_cache[swf]
        else:
            tmp_dir = os.path.join(tempfile.gettempdir(), "carmodder_icons")
            os.makedirs(tmp_dir, exist_ok=True)
            png = export_image(swf, tmp_dir)
            if png:
                self._icon_cache[swf] = png
        self.after(0, lambda: self._show_icon(swf, png))

    def _show_icon(self, swf: str, png: str | None):
        self._icon_cv.delete("all")
        if not png or not os.path.exists(png):
            self._icon_cv.create_text(40, 40, text="no image", fill="#444",
                                       font=("Segoe UI", 7))
            self._icon_lbl.config(text="No image found in SWF")
            self._current_icon_swf = None
            return
        try:
            img = Image.open(png).convert("RGBA").resize((80, 80), Image.LANCZOS)
            self._icon_tk = ImageTk.PhotoImage(img)
            self._icon_cv.create_image(0, 0, anchor="nw", image=self._icon_tk)
            self._current_icon_swf = swf
            self._icon_lbl.config(text=os.path.basename(swf))
        except Exception as e:
            self._icon_cv.create_text(40, 40, text="error", fill="#e94560",
                                       font=("Segoe UI", 7))
            self._icon_lbl.config(text=str(e))

    def _attach_icon(self):
        """Store the current icon's SWF filename as 'icon' attr on the selected part."""
        if self._sel_idx is None:
            messagebox.showwarning("No part selected", "Select a part first.",
                                   parent=self)
            return
        swf = getattr(self, '_current_icon_swf', None)
        if not swf:
            messagebox.showinfo("No icon loaded", "Load a cache icon first.",
                                parent=self)
            return
        self._parts[self._sel_idx]['icon'] = os.path.basename(swf)
        self._refresh_lb()
        self._icon_lbl.config(text=f"Attached: {os.path.basename(swf)}")

    # ── Build SWF methods ──────────────────────────────────────────────────────

    def _browse_build_img(self):
        path = filedialog.askopenfilename(
            title="Select part image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.webp"), ("All", "*.*")],
            parent=self)
        if path:
            self._build_img_var.set(path)
            try:
                img = Image.open(path)
                self._bld_sw.set(img.width)
                self._bld_sh.set(img.height)
            except Exception:
                pass

    def _browse_build_out(self):
        path = filedialog.asksaveasfilename(
            title="Save part SWF as",
            defaultextension=".swf",
            filetypes=[("SWF files", "*.swf"), ("All files", "*.*")],
            parent=self)
        if path:
            self._build_out_var.set(path)

    def _use_cache_icon_for_build(self):
        swf = getattr(self, '_current_icon_swf', None)
        if swf and swf in self._icon_cache:
            png = self._icon_cache[swf]
            self._build_img_var.set(png)
            try:
                img = Image.open(png)
                self._bld_sw.set(img.width)
                self._bld_sh.set(img.height)
            except Exception:
                pass

    def _do_build_swf(self):
        img_path = self._build_img_var.get().strip()
        out_path = self._build_out_var.get().strip()
        if not img_path or not os.path.exists(img_path):
            self._build_status.config(text="No valid source image.", foreground="#e94560")
            return
        if not out_path:
            self._build_status.config(text="No output path set.", foreground="#e94560")
            return
        self._build_status.config(text="Building…", foreground="#aaa")
        self.update_idletasks()
        try:
            img = Image.open(img_path).convert("RGBA")
            ok = build_part_swf(
                img, out_path,
                stage_w=self._bld_sw.get() or None,
                stage_h=self._bld_sh.get() or None,
                offset_x=self._bld_ox.get(),
                offset_y=self._bld_oy.get(),
            )
            if ok:
                size_kb = os.path.getsize(out_path) // 1024
                self._build_status.config(
                    text=f"Built: {os.path.basename(out_path)}  ({size_kb} KB)",
                    foreground="#00ff88")
            else:
                self._build_status.config(text="Build failed.", foreground="#e94560")
        except Exception as e:
            self._build_status.config(text=str(e), foreground="#e94560")

    def _fields_as_dict(self) -> dict:
        d = {}
        for key, var in self._field_vars.items():
            v = var.get()
            if key in ('n', 't') or (v != 0 and v != 0.0 and v != ""):
                d[key] = str(v) if not isinstance(v, str) else v
        return d

    def _set_fields(self, attrs: dict):
        for key, var in self._field_vars.items():
            val = attrs.get(key, None)
            try:
                if val is None:
                    if isinstance(var, tk.IntVar):    var.set(0)
                    elif isinstance(var, tk.DoubleVar): var.set(0.0)
                    else:                              var.set("")
                elif isinstance(var, tk.IntVar):   var.set(int(val))
                elif isinstance(var, tk.DoubleVar): var.set(float(val))
                else:                               var.set(str(val))
            except Exception:
                pass

    def _refresh_lb(self):
        self._lb.delete(0, tk.END)
        for p in self._parts:
            self._lb.insert(tk.END, f"  [{p.get('t','')}] {p.get('n','unnamed')}")

    def _on_select(self, *_):
        sel = self._lb.curselection()
        if not sel:
            return
        self._sel_idx = sel[0]
        part = self._parts[self._sel_idx]
        self._set_fields(part)
        # Auto-show attached icon
        icon_fname = part.get('icon')
        if icon_fname:
            swf = os.path.join(self._parts_dir, icon_fname)
            if os.path.exists(swf):
                threading.Thread(target=self._extract_icon, args=(swf,), daemon=True).start()

    def _new_part(self):
        self._parts.append({'n': 'New Part', 't': 'engine'})
        self._refresh_lb()
        self._lb.selection_set(len(self._parts) - 1)
        self._on_select()

    def _duplicate(self):
        if self._sel_idx is None:
            return
        copy = dict(self._parts[self._sel_idx])
        copy['n'] = copy.get('n', '') + ' Copy'
        self._parts.append(copy)
        self._refresh_lb()
        self._lb.selection_set(len(self._parts) - 1)
        self._on_select()

    def _remove(self):
        if self._sel_idx is None:
            return
        self._parts.pop(self._sel_idx)
        self._sel_idx = None
        self._refresh_lb()

    def _apply_fields(self):
        if self._sel_idx is None:
            return
        new_data = self._fields_as_dict()
        # Preserve icon attachment — it lives outside the field vars
        existing_icon = self._parts[self._sel_idx].get('icon')
        if existing_icon:
            new_data['icon'] = existing_icon
        self._parts[self._sel_idx] = new_data
        self._refresh_lb()

    def _add_from_fields(self):
        self._parts.append(self._fields_as_dict())
        self._refresh_lb()
        self._lb.selection_set(len(self._parts) - 1)

    def _save_group(self):
        name = self._grp_name.get().strip()
        if not name or not self._parts:
            return
        self._groups[name] = [dict(p) for p in self._parts]
        self._grp_combo['values'] = list(self._groups)
        self._grp_combo.set(name)

    def _load_group(self):
        name = self._grp_combo.get()
        if name in self._groups:
            self._parts = [dict(p) for p in self._groups[name]]
            self._refresh_lb()

    def _part_to_xml(self, attrs: dict) -> str:
        pairs = ' '.join(f"{k}='{v}'" for k, v in attrs.items() if v != '')
        return f"<p {pairs}/>"

    def _generate_xml(self):
        self._xml_out.delete('1.0', tk.END)
        self._xml_out.insert('1.0', '\n'.join(self._part_to_xml(p) for p in self._parts))

    def _copy_xml(self):
        self._generate_xml()
        self.clipboard_clear()
        self.clipboard_append(self._xml_out.get('1.0', tk.END).strip())

    def _import_xml(self):
        import re
        path = filedialog.askopenfilename(
            title="Import parts XML",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")])
        if not path:
            return
        try:
            text = open(path, encoding='utf-8', errors='ignore').read()
        except Exception:
            return
        for entry in re.findall(r"<p\s+([^/]+)/>", text):
            attrs = dict(re.findall(r"(\w+)='([^']*)'", entry))
            if not attrs:
                attrs = dict(re.findall(r'(\w+)="([^"]*)"', entry))
            if attrs:
                self._parts.append(attrs)
        self._refresh_lb()


# ── Paint tinting (legends-builder algorithm) ─────────────────────────────────

def _paint_tint(img: Image.Image, color: tuple) -> Image.Image:
    """Tint only red-dominant pixels (R > G×1.4 AND R > B×1.4) — the game's actual paint surfaces."""
    arr = np.array(img.convert('RGBA'), dtype=np.float32)
    R, G, B, A = arr[...,0], arr[...,1], arr[...,2], arr[...,3]
    mask = (R > G * 1.4) & (R > B * 1.4) & (A > 0)
    Rc, Gc, Bc = color
    out = arr.copy()
    out[mask, 0] = np.clip((Rc / 255.0) * R[mask], 0, 255)
    out[mask, 1] = np.clip((Gc / 255.0) * R[mask], 0, 255)
    out[mask, 2] = np.clip((Bc / 255.0) * R[mask], 0, 255)
    return Image.fromarray(out.astype(np.uint8), 'RGBA')


def _paint_mask_vis(img: Image.Image) -> Image.Image:
    """Visualise which pixels are paintable (bright green) vs non-paint (dimmed grey)."""
    arr = np.array(img.convert('RGBA'), dtype=np.float32)
    R, G, B, A = arr[...,0], arr[...,1], arr[...,2], arr[...,3]
    mask = (R > G * 1.4) & (R > B * 1.4) & (A > 0)
    out  = np.zeros_like(arr)
    out[mask]  = [0, 255, 100, 255]
    grey = (R * 0.299 + G * 0.587 + B * 0.114) * 0.35
    non  = ~mask & (A > 0)
    out[non, 0] = grey[non]; out[non, 1] = grey[non]
    out[non, 2] = grey[non]; out[non, 3] = A[non]
    return Image.fromarray(out.astype(np.uint8), 'RGBA')


# ── Paint Lab (experimental tab 3) ────────────────────────────────────────────

class PaintLabFrame(ttk.Frame):
    """Experimental: legends-builder paint algorithm + stage preview + partsXml editor."""

    STAGE_W, STAGE_H = 800, 500

    def __init__(self, parent, get_slots, get_pkg_info, get_src_id, tmp_dir, **kw):
        super().__init__(parent, **kw)
        self._get_slots   = get_slots
        self._get_pkg_info = get_pkg_info
        self._get_src_id  = get_src_id
        self._tmp         = tmp_dir
        self._tk_img      = None
        self._paint_color = (200, 30, 30)
        self._show_mask   = tk.BooleanVar(value=False)
        self._xml_fields: dict[str, tk.StringVar] = {}
        self._xml_widgets = []
        self.configure(style='TFrame')
        self._build_ui()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # Top bar
        top = ttk.Frame(self, padding=(8, 6, 8, 4))
        top.grid(row=0, column=0, sticky='ew')

        ttk.Button(top, text='↺ Sync from Car Modder',
                   style='Accent.TButton',
                   command=self._sync_and_render).pack(side='left', padx=(0, 10))

        paint_lf = ttk.LabelFrame(top, text='Paint Color', padding=(6, 2))
        paint_lf.pack(side='left', padx=(0, 10))
        self._swatch = tk.Button(paint_lf, bg='#c81e1e', width=3, height=1,
                                  relief='flat', cursor='hand2',
                                  command=self._pick_color)
        self._swatch.pack(side='left', padx=(0, 4))
        self._hex_lbl = ttk.Label(paint_lf, text='#c81e1e', foreground=ACC,
                                   font=('Consolas', 8))
        self._hex_lbl.pack(side='left')

        ttk.Checkbutton(top, text='Show paint mask',
                        variable=self._show_mask,
                        command=self._render).pack(side='left', padx=(0, 10))

        ttk.Label(top,
                  text='Algorithm: R > G×1.4 AND R > B×1.4 (only tints actual painted surfaces)',
                  foreground='#555', font=('Segoe UI', 8)).pack(side='left')

        ttk.Button(top, text='Export PNG…',
                   command=self._export).pack(side='right')

        # Body
        body = ttk.Frame(self)
        body.grid(row=1, column=0, sticky='nsew', padx=8, pady=(0, 8))
        body.columnconfigure(0, weight=0)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        # Canvas
        cv_lf = ttk.LabelFrame(body, text='Stage Preview  (800×500 — front view)',
                                padding=4)
        cv_lf.grid(row=0, column=0, sticky='n', padx=(0, 8))
        self._cv = tk.Canvas(cv_lf, width=self.STAGE_W, height=self.STAGE_H,
                              bg=DARK, highlightthickness=1, highlightbackground='#333')
        self._cv.pack()
        self._status_lbl = ttk.Label(cv_lf, text='Click "Sync from Car Modder" to preview.',
                                      foreground='#555', font=('Segoe UI', 8))
        self._status_lbl.pack(anchor='w', pady=(4, 0))

        # Right panel
        right = ttk.Frame(body)
        right.grid(row=0, column=1, sticky='nsew')
        right.columnconfigure(0, weight=1)

        # Paint pixel count info
        info_lf = ttk.LabelFrame(right, text='Paint Stats', padding=8)
        info_lf.grid(row=0, column=0, sticky='ew', pady=(0, 8))
        self._stats_lbl = ttk.Label(info_lf, text='—', foreground='#666',
                                     font=('Consolas', 8), justify='left')
        self._stats_lbl.pack(anchor='w')

        # partsXml editor
        xml_lf = ttk.LabelFrame(right, text='Parts XML Editor', padding=8)
        xml_lf.grid(row=1, column=0, sticky='nsew')
        xml_lf.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        ttk.Label(xml_lf, text='Paste a <p .../> element from partsXml:',
                  foreground='#888', font=('Segoe UI', 8)).pack(anchor='w')

        self._xml_txt = tk.Text(xml_lf, height=5, bg='#16213e', fg=ACC,
                                 insertbackground=FG, font=('Consolas', 8),
                                 relief='flat', wrap='char')
        self._xml_txt.pack(fill='x', pady=(4, 4))

        ttk.Button(xml_lf, text='Parse fields →', style='Accent.TButton',
                   command=self._parse_xml).pack(anchor='w', pady=(0, 8))

        self._fields_outer = ttk.Frame(xml_lf)
        self._fields_outer.pack(fill='both', expand=True)
        self._fields_outer.columnconfigure(1, weight=1)
        self._fields_outer.columnconfigure(3, weight=1)

        # Rebuild XML button
        ttk.Button(xml_lf, text='Copy rebuilt XML →',
                   command=self._rebuild_xml).pack(anchor='w', pady=(8, 0))
        self._rebuilt_txt = tk.Text(xml_lf, height=4, bg='#16213e', fg='#00ff88',
                                     insertbackground=FG, font=('Consolas', 8),
                                     relief='flat', wrap='char', state='disabled')
        self._rebuilt_txt.pack(fill='x', pady=(4, 0))

    # ── Paint ─────────────────────────────────────────────────────────────────

    def _pick_color(self):
        from tkinter.colorchooser import askcolor
        init = '#{:02x}{:02x}{:02x}'.format(*self._paint_color)
        result = askcolor(color=init, title='Pick paint colour', parent=self)
        if result and result[0]:
            self._paint_color = tuple(int(v) for v in result[0])
            hex_c = '#{:02x}{:02x}{:02x}'.format(*self._paint_color)
            self._swatch.config(bg=hex_c)
            self._hex_lbl.config(text=hex_c)
            self._render()

    def _sync_and_render(self):
        self._status_lbl.config(text='Assembling stage…')
        self.update_idletasks()
        threading.Thread(target=self._render_worker, daemon=True).start()

    def _render(self, *_):
        threading.Thread(target=self._render_worker, daemon=True).start()

    # Bottom-to-top layer order for car part SWFs
    _LAYER_ORDER = ['shadow', 'underCarriage', 'bumperRear', 'bumper',
                    'body', 'line', 'roofEffect', 'roof']

    @staticmethod
    def _layer_key(swf_path: str) -> int:
        name = os.path.basename(swf_path).lower()
        for i, k in enumerate(PaintLabFrame._LAYER_ORDER):
            if k.lower() in name:
                return i
        return 4

    def _render_worker(self):
        try:
            self._render_worker_inner()
        except Exception as e:
            import traceback
            msg = f'Render error: {e}'
            self.after(0, lambda m=msg: self._status_lbl.config(text=m))

    def _render_worker_inner(self):
        slots = self._get_slots()

        if not slots:
            self.after(0, lambda: self._status_lbl.config(
                text='No car loaded — use Car Modder tab first.'))
            return

        # One representative slot per unique front-view SWF, in layer order
        seen: dict[str, object] = {}
        for s in slots:
            if '[F]' in s.label and s.swf_path not in seen:
                seen[s.swf_path] = s

        if not seen:
            all_labels = [s.label for s in slots[:5]]
            self.after(0, lambda ll=all_labels: self._status_lbl.config(
                text=f'No [F] slots found. Labels: {ll}'))
            return

        ordered = sorted(seen.keys(), key=self._layer_key)
        frames = []   # (img, ox, oy)
        canvas_x2 = canvas_y2 = 0
        info_lines = []

        for swf_path in ordered:
            fname = os.path.basename(swf_path)
            slot  = seen[swf_path]

            # Load raw image
            try:
                img = slot.orig_image()
            except Exception as e:
                info_lines.append(f'{fname}: img load failed ({e})')
                continue

            # Get game-coordinate origin from SWF RECT; fall back to (0,0)
            ox = oy = 0
            try:
                w_px, h_px, _bg, ox, oy = read_swf_info(swf_path)
                if img.width != w_px or img.height != h_px:
                    img = img.resize((w_px, h_px), Image.LANCZOS)
            except Exception as e:
                info_lines.append(f'{fname}: rect failed ({e}), using (0,0)')

            frames.append((img, ox, oy))
            canvas_x2 = max(canvas_x2, ox + img.width)
            canvas_y2 = max(canvas_y2, oy + img.height)
            info_lines.append(f'{fname} OK @ ({ox},{oy})')

        if not frames or canvas_x2 < 1 or canvas_y2 < 1:
            msg = f'No renderable layers. ' + ' | '.join(info_lines)
            self.after(0, lambda m=msg: self._status_lbl.config(text=m))
            return

        # Composite: paste each part at its RECT-derived game-coordinate origin
        canvas = Image.new('RGBA', (canvas_x2, canvas_y2), (0, 0, 0, 0))
        paint_pixels = total_pixels = 0

        for img, ox, oy in frames:
            arr = np.array(img, dtype=np.float32)
            R, G, B, A = arr[...,0], arr[...,1], arr[...,2], arr[...,3]
            m = (R > G * 1.4) & (R > B * 1.4) & (A > 10)
            paint_pixels += int(m.sum())
            total_pixels += int((A > 10).sum())

            layer = _paint_mask_vis(img) if self._show_mask.get() \
                    else _paint_tint(img, self._paint_color)
            canvas.paste(layer, (ox, oy), layer)

        # Scale to paint lab canvas, preserving aspect ratio, centred
        bg_stage = Image.new('RGBA', (self.STAGE_W, self.STAGE_H), (20, 20, 35, 255))
        cw, ch = canvas.size
        scale = min(self.STAGE_W / cw, self.STAGE_H / ch) if cw and ch else 1
        dw = int(cw * scale); dh = int(ch * scale)
        scaled = canvas.resize((dw, dh), Image.LANCZOS)
        px = (self.STAGE_W - dw) // 2
        py = (self.STAGE_H - dh) // 2
        bg_stage.paste(scaled, (px, py), scaled)

        pct = (paint_pixels / total_pixels * 100) if total_pixels else 0
        stats = (f'Paint pixels: {paint_pixels:,}\n'
                 f'Total visible: {total_pixels:,}\n'
                 f'Paint coverage: {pct:.1f}%\n'
                 f'Colour: #{self._paint_color[0]:02x}{self._paint_color[1]:02x}{self._paint_color[2]:02x}')

        tk_img = ImageTk.PhotoImage(bg_stage)
        self.after(0, lambda: self._show_stage(tk_img, stats,
                                                f'{len(frames)} SWF frames composited'))

    def _show_stage(self, tk_img, stats, msg):
        self._tk_img = tk_img
        self._cv.delete('all')
        self._cv.create_image(0, 0, anchor='nw', image=tk_img)
        self._stats_lbl.config(text=stats)
        self._status_lbl.config(text=msg)

    # ── partsXml editor ───────────────────────────────────────────────────────

    # Attributes we expose for editing (label, type, min, max)
    _EDITABLE = {
        'ps': ('Size (ps)', 'int',   0,  999),
        'ar': ('Aspect ratio (ar)', 'int',  0,   20),
        'hp': ('Horsepower (hp)', 'int',   0, 9999),
        'tq': ('Torque (tq)',     'int',   0, 9999),
        'wt': ('Weight (wt)',     'int',   0, 9999),
        'l':  ('Level (l)',       'int',   0, 9999),
        'p':  ('Price (p)',       'int',   0, 999999),
        'scx':('Scale X (scx)',   'float', 0.0, 10.0),
        'scy':('Scale Y (scy)',   'float', 0.0, 10.0),
    }

    def _parse_xml(self):
        import re
        raw = self._xml_txt.get('1.0', tk.END).strip()
        # Extract all attr='value' pairs
        attrs = dict(re.findall(r"(\w+)='([^']*)'", raw))
        if not attrs:
            attrs = dict(re.findall(r'(\w+)="([^"]*)"', raw))
        if not attrs:
            return

        # Clear existing field widgets
        for w in self._xml_widgets:
            try: w.destroy()
            except: pass
        self._xml_widgets.clear()
        self._xml_fields.clear()

        # Store all attrs (including non-editable) for rebuild
        self._all_attrs = attrs

        # Build editable fields in a 2-column grid
        row = 0
        for key, (label, typ, mn, mx) in self._EDITABLE.items():
            if key not in attrs:
                continue
            var = tk.StringVar(value=attrs[key])
            self._xml_fields[key] = var
            lbl = ttk.Label(self._fields_outer, text=label)
            lbl.grid(row=row, column=0, sticky='w', padx=(0, 4), pady=2)
            if typ == 'int':
                sp = tk.Spinbox(self._fields_outer, textvariable=var,
                                from_=mn, to=mx, increment=1, width=8,
                                bg='#16213e', fg=ACC, buttonbackground='#0f3460',
                                relief='flat', font=('Consolas', 9))
            else:
                sp = tk.Spinbox(self._fields_outer, textvariable=var,
                                from_=mn, to=mx, increment=0.1, width=8,
                                bg='#16213e', fg=ACC, buttonbackground='#0f3460',
                                relief='flat', font=('Consolas', 9), format='%.2f')
            sp.grid(row=row, column=1, sticky='w', pady=2)
            self._xml_widgets += [lbl, sp]
            row += 1

        # Show non-editable attrs as read-only info
        other = {k: v for k, v in attrs.items() if k not in self._EDITABLE and k != 'n'}
        if attrs.get('n'):
            lbl = ttk.Label(self._fields_outer,
                            text=f"Name: {attrs['n']}", foreground=ACC,
                            font=('Segoe UI', 9, 'bold'))
            lbl.grid(row=row, column=0, columnspan=2, sticky='w', pady=(4, 2))
            self._xml_widgets.append(lbl)
            row += 1

    def _rebuild_xml(self):
        if not hasattr(self, '_all_attrs') or not self._all_attrs:
            return
        updated = dict(self._all_attrs)
        for key, var in self._xml_fields.items():
            updated[key] = var.get()
        attrs_str = ' '.join(f"{k}='{v}'" for k, v in updated.items())
        rebuilt = f"<p {attrs_str}/>"
        self._rebuilt_txt.config(state='normal')
        self._rebuilt_txt.delete('1.0', tk.END)
        self._rebuilt_txt.insert('1.0', rebuilt)
        self._rebuilt_txt.config(state='disabled')
        self.clipboard_clear()
        self.clipboard_append(rebuilt)

    # ── Export ────────────────────────────────────────────────────────────────

    def _export(self):
        path = filedialog.asksaveasfilename(
            title='Export stage PNG',
            defaultextension='.png',
            filetypes=[('PNG', '*.png'), ('All files', '*.*')])
        if not path:
            return
        # Re-render at full size and save
        slots    = self._get_slots()
        pkg_info = self._get_pkg_info()
        car_id   = self._get_src_id()
        if not slots:
            return
        stage = Image.new('RGBA', (self.STAGE_W, self.STAGE_H), (0, 0, 0, 0))
        for slot in [s for s in slots if '[F]' in s.label]:
            tinted = _paint_tint(slot.orig_image(), self._paint_color)
            stage.paste(tinted, (0, 0), tinted)
        stage.save(path, 'PNG')
        messagebox.showinfo('Exported', f'Stage PNG saved to:\n{path}')


# ── Badge editor ───────────────────────────────────────────────────────────────

@dataclasses.dataclass
class BadgeData:
    badge_id:    int
    small_char:  int  | None        # None = new badge (not yet in SWF)
    small_path:  str  | None = None # original small (None for new badges)
    large_char:  int  | None = None
    large_path:  str  | None = None
    custom_path: str  | None = None # replacement image for existing badge
    # New badge fields
    is_new:      bool = False
    new_small:   str  | None = None # user-supplied small image path
    new_large:   str  | None = None # user-supplied large image path (or None = auto)


# ── Rim Editor ────────────────────────────────────────────────────────────────

class RimEditorFrame(ttk.Frame):
    VIEWS     = [('FF', 'Front / Front wheel'), ('FR', 'Front / Rear wheel'),
                 ('BF', 'Back / Front wheel'),  ('BR', 'Back / Rear wheel')]
    THUMB     = 80
    WHEEL_DIR = os.path.join(CACHE_DIR, "car", "wheel")

    def __init__(self, parent, tmp_dir: str, **kw):
        super().__init__(parent, **kw)
        self._tmp      = tmp_dir
        self._rim_id   = tk.IntVar(value=1)
        self._new_id   = tk.IntVar(value=200)
        self._previews: dict[str, Image.Image | None] = {v: None for v, _ in self.VIEWS}
        self._custom:   dict[str, str | None]         = {v: None for v, _ in self.VIEWS}
        self._hue = {v: tk.DoubleVar(value=0)   for v, _ in self.VIEWS}
        self._sat = {v: tk.DoubleVar(value=0)   for v, _ in self.VIEWS}
        self._bri = {v: tk.DoubleVar(value=0)   for v, _ in self.VIEWS}
        self._tk_imgs: list = []
        self._build_ui()

    # ── UI ─────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # ── Top bar ────────────────────────────────────────────────────────────
        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky='ew', pady=(0, 6))

        ttk.Label(top, text='Source Rim ID:').pack(side='left')
        ttk.Spinbox(top, textvariable=self._rim_id, from_=1, to=300,
                    width=5).pack(side='left', padx=(4, 0))
        ttk.Button(top, text='Load', style='Accent.TButton',
                   command=self._load_rim).pack(side='left', padx=(6, 0))

        ttk.Separator(top, orient='vertical').pack(side='left', fill='y', padx=12)

        ttk.Label(top, text='New Rim ID:').pack(side='left')
        ttk.Spinbox(top, textvariable=self._new_id, from_=1, to=9999,
                    width=6).pack(side='left', padx=(4, 0))
        ttk.Button(top, text='Build & Save to Cache', style='Warn.TButton',
                   command=self._build_rim).pack(side='left', padx=(6, 0))

        self._status = ttk.Label(top, text='Load a rim to start editing.',
                                  foreground='#aaa')
        self._status.pack(side='left', padx=(12, 0))

        # ── View panels ────────────────────────────────────────────────────────
        views_fr = ttk.Frame(self)
        views_fr.grid(row=1, column=0, sticky='nsew')
        for ci in range(4):
            views_fr.columnconfigure(ci, weight=1)
        views_fr.rowconfigure(0, weight=1)

        self._view_panels: dict[str, dict] = {}
        for ci, (view, label) in enumerate(self.VIEWS):
            lf = ttk.LabelFrame(views_fr, text=label, padding=6)
            lf.grid(row=0, column=ci, sticky='nsew', padx=(0, 6) if ci < 3 else 0)
            lf.rowconfigure(0, weight=1)
            lf.columnconfigure(0, weight=1)

            # Preview canvas
            cv = tk.Canvas(lf, bg=DARK, width=160, height=160, highlightthickness=0)
            cv.grid(row=0, column=0, pady=(0, 6))

            # Colour sliders
            def _slider(parent, var, label, row):
                ttk.Label(parent, text=label, foreground='#888',
                          font=('Segoe UI', 7)).grid(row=row, column=0, sticky='w')
                sl = tk.Scale(parent, variable=var, from_=-180, to=180,
                              orient='horizontal', length=150, bg=BG, fg=FG,
                              troughcolor=DARK, showvalue=1, font=('Segoe UI', 7),
                              activebackground=ACC, highlightthickness=0,
                              command=lambda *_: self._refresh_preview(view))
                sl.grid(row=row, column=1, padx=(4, 0))

            _slider(lf, self._hue[view], 'Hue',  1)
            _slider(lf, self._sat[view], 'Sat',  2)
            _slider(lf, self._bri[view], 'Bri',  3)

            # Buttons
            btn_fr = ttk.Frame(lf)
            btn_fr.grid(row=4, column=0, columnspan=2, sticky='ew', pady=(6, 0))
            ttk.Button(btn_fr, text='Upload…',
                       command=lambda v=view: self._upload(v)).pack(side='left', fill='x',
                                                                     expand=True, padx=(0, 2))
            ttk.Button(btn_fr, text='Reset',
                       command=lambda v=view: self._reset_view(v)).pack(side='left')

            self._view_panels[view] = {'cv': cv, 'lf': lf}

    # ── Actions ────────────────────────────────────────────────────────────────

    def _load_rim(self):
        rim_id = self._rim_id.get()
        self._tk_imgs.clear()
        missing = []
        for view, _ in self.VIEWS:
            path = os.path.join(self.WHEEL_DIR, f"wheel{view}_{rim_id}.swf")
            if not os.path.exists(path):
                missing.append(view)
                self._previews[view] = None
                self._custom[view]   = None
                self._view_panels[view]['lf'].configure(text=f'{view} — not found')
                self._clear_canvas(view)
                continue
            out_dir = os.path.join(self._tmp, f"rim_{rim_id}_{view}")
            imgs = export_all_images(path, out_dir)
            if imgs:
                img = Image.open(list(imgs.values())[0]).convert('RGBA')
            else:
                img = Image.new('RGBA', (160, 160), (30, 30, 30, 255))
            self._previews[view] = img
            self._custom[view]   = None
            _, label = next((v, l) for v, l in self.VIEWS if v == view)
            self._view_panels[view]['lf'].configure(text=label)
            self._refresh_preview(view)
        msg = f'Rim {rim_id} loaded.'
        if missing:
            msg += f'  (no {view} SWF: {", ".join(missing)})'
        self._status.config(text=msg, foreground='#aaa')

    def _refresh_preview(self, view: str):
        src = self._previews.get(view)
        if src is None:
            return
        custom_path = self._custom.get(view)
        img = Image.open(custom_path).convert('RGBA') if custom_path else src.copy()
        img = apply_color_adjustments(img,
                                      self._hue[view].get(),
                                      self._sat[view].get(),
                                      self._bri[view].get())
        img = img.resize((160, 160), Image.LANCZOS)
        tkimg = ImageTk.PhotoImage(img)
        self._tk_imgs.append(tkimg)
        cv = self._view_panels[view]['cv']
        cv.delete('all')
        cv.create_image(0, 0, anchor='nw', image=tkimg)

    def _clear_canvas(self, view: str):
        cv = self._view_panels[view]['cv']
        cv.delete('all')
        cv.create_text(80, 80, text='N/A', fill='#333', font=('Segoe UI', 12))

    def _upload(self, view: str):
        path = filedialog.askopenfilename(
            title=f'Replace rim {view} image',
            filetypes=[('Images', '*.png *.jpg *.jpeg *.bmp *.webp'), ('All', '*.*')])
        if not path:
            return
        self._custom[view] = path
        self._refresh_preview(view)

    def _reset_view(self, view: str):
        self._custom[view] = None
        self._hue[view].set(0)
        self._sat[view].set(0)
        self._bri[view].set(0)
        self._refresh_preview(view)

    def _build_rim(self):
        new_id = self._new_id.get()
        src_id = self._rim_id.get()
        built, errors = [], []
        for view, _ in self.VIEWS:
            src_swf = os.path.join(self.WHEEL_DIR, f"wheel{view}_{src_id}.swf")
            if not os.path.exists(src_swf):
                errors.append(f'{view}:missing')
                continue
            out_dir = os.path.join(self._tmp, f"rim_{src_id}_{view}")
            imgs = export_all_images(src_swf, out_dir)
            if not imgs:
                errors.append(f'{view}:no-img')
                continue
            char_id = list(imgs.keys())[0]
            src = self._previews.get(view)
            custom_path = self._custom.get(view)
            if custom_path:
                final = Image.open(custom_path).convert('RGBA')
            elif src:
                final = src.copy()
            else:
                errors.append(f'{view}:no-preview')
                continue
            final = apply_color_adjustments(final,
                                            self._hue[view].get(),
                                            self._sat[view].get(),
                                            self._bri[view].get())
            # Save as JPEG (matching original format)
            tmp_img = os.path.join(self._tmp, f"rim_bld_{new_id}_{view}.jpg")
            final.convert('RGB').save(tmp_img, 'JPEG', quality=95)
            out_swf = os.path.join(self.WHEEL_DIR, f"wheel{view}_{new_id}.swf")
            ok = replace_all_images_in_swf(src_swf, {char_id: tmp_img}, out_swf)
            if ok:
                built.append(f'wheel{view}_{new_id}.swf')
            else:
                errors.append(f'{view}:build-fail')

        msg = f'Built rim {new_id}: {", ".join(built)}.'
        if errors:
            msg += f'  Errors: {", ".join(errors)}'
        self._status.config(text=msg, foreground='#00c87a' if not errors else '#e94560')


class BadgeEditorFrame(ttk.Frame):
    THUMB = 40
    PAD   = 5
    COLS  = 10   # default; recalculated on resize

    def __init__(self, parent, tmp_dir: str, **kw):
        super().__init__(parent, **kw)
        self._tmp       = tmp_dir
        self._badges:   dict[int, BadgeData] = {}
        self._thumbs:   list = []   # keep PhotoImage refs alive
        self._sel_id:   int | None = None
        self._cols:     int = self.COLS
        self._ids:      list[int] = []
        self._gaps:     list[int] = []   # gap IDs available in 1-count range
        self._swf_count: int = 622
        self.configure(style="TFrame")
        self._build_ui()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # ── Top bar ────────────────────────────────────────────────────────────
        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        ttk.Button(top, text="Load badges.swf", style="Accent.TButton",
                   command=self._load).pack(side="left", padx=(0, 4))
        ttk.Button(top, text="+ Add New Badge",
                   command=self._add_badge_dialog).pack(side="left", padx=(0, 8))
        self._status = ttk.Label(top, text="Click 'Load badges.swf' to begin.",
                                  foreground="#aaa")
        self._status.pack(side="left")
        self._save_btn = ttk.Button(top, text="Save to cache",
                                     style="Warn.TButton", command=self._save,
                                     state="disabled")
        self._save_btn.pack(side="right")

        # ── Content split ──────────────────────────────────────────────────────
        split = ttk.Frame(self)
        split.grid(row=1, column=0, sticky="nsew")
        split.columnconfigure(0, weight=1)
        split.columnconfigure(1, weight=0)
        split.rowconfigure(0, weight=1)

        # Grid panel
        grid_lf = ttk.LabelFrame(split, text="All Badges", padding=4)
        grid_lf.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        grid_lf.rowconfigure(0, weight=1)
        grid_lf.columnconfigure(0, weight=1)

        self._cv = tk.Canvas(grid_lf, bg=DARK, highlightthickness=0)
        self._cv.grid(row=0, column=0, sticky="nsew")
        vsb = ttk.Scrollbar(grid_lf, orient="vertical", command=self._cv.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        self._cv.configure(yscrollcommand=vsb.set)
        self._cv.bind("<Configure>",   lambda e: self._draw_grid())
        self._cv.bind("<Button-1>",    self._on_click)
        self._cv.bind("<MouseWheel>",  lambda e: self._cv.yview_scroll(
            -1 if e.delta > 0 else 1, "units"))

        # Preview panel
        prev_lf = ttk.LabelFrame(split, text="Selected Badge", padding=8)
        prev_lf.grid(row=0, column=1, sticky="nsew")
        prev_lf.columnconfigure(0, weight=1)

        self._prev_cv = tk.Canvas(prev_lf, bg=DARK, width=220, height=220,
                                   highlightthickness=0)
        self._prev_cv.grid(row=0, column=0, pady=(0, 8))
        self._prev_tk = None

        self._sel_lbl = ttk.Label(prev_lf, text="No badge selected",
                                   foreground=ACC, font=("Segoe UI", 9, "bold"))
        self._sel_lbl.grid(row=1, column=0, sticky="w")

        self._custom_lbl = ttk.Label(prev_lf, text="", foreground="#666", wraplength=220)
        self._custom_lbl.grid(row=2, column=0, sticky="w", pady=(2, 8))

        ttk.Button(prev_lf, text="Export Badge Image…",
                   command=self._export).grid(row=3, column=0, sticky="ew")
        ttk.Button(prev_lf, text="Replace with custom image…",
                   style="Accent.TButton",
                   command=self._replace).grid(row=4, column=0, sticky="ew", pady=(4, 0))
        ttk.Button(prev_lf, text="Clear replacement",
                   command=self._clear).grid(row=5, column=0, sticky="ew", pady=(4, 0))

    # ── Load ───────────────────────────────────────────────────────────────────

    def _load(self):
        self._status.config(text="Exporting badge images — please wait…", foreground="#aaa")
        self.update()
        threading.Thread(target=self._load_worker, daemon=True).start()

    def _load_worker(self):
        swf = os.path.join(CACHE_DIR, "badges", "badges.swf")
        if not os.path.exists(swf):
            self.after(0, lambda: self._status.config(
                text=f"⚠ Not found: {swf}", foreground="#e94560"))
            return
        out   = os.path.join(self._tmp, "badges_export")
        data  = export_badge_images(swf, out)
        gaps  = get_swf_badge_gap_ids(swf)
        from swf_utils import _swf_load, _swf_tags_start, _swf_get_count
        raw   = _swf_load(swf)
        count = _swf_get_count(raw, _swf_tags_start(raw))
        self.after(0, lambda: self._on_loaded(data, gaps, count))

    def _on_loaded(self, data: dict[int, dict], gaps: list[int], swf_count: int):
        self._gaps      = gaps
        self._swf_count = swf_count
        # Preserve any new badges the user already added this session
        new_badges = {bid: bd for bid, bd in self._badges.items() if bd.is_new}
        self._badges = {}
        for bid, info in data.items():
            if "small" not in info:
                continue
            sc, sp = info["small"]
            lc, lp = info["large"] if "large" in info else (None, None)
            self._badges[bid] = BadgeData(bid, sc, sp, lc, lp)
        self._badges.update(new_badges)
        self._ids = sorted(self._badges)
        n_new = len(new_badges)
        gap_txt = f"  |  {len(gaps)} free gap slot(s) available"
        new_txt = f"  |  {n_new} new badge(s) queued" if n_new else ""
        self._status.config(
            text=f"{len(data)} badges loaded.{gap_txt}{new_txt}",
            foreground="#4caf50")
        self._draw_grid()

    # ── Grid ───────────────────────────────────────────────────────────────────

    def _draw_grid(self):
        if not self._badges:
            return
        T, P = self.THUMB, self.PAD
        step  = T + P
        avail = max(self._cv.winfo_width() - P, step)
        cols  = max(1, avail // step)
        self._cols = cols

        self._cv.delete("all")
        self._thumbs.clear()

        for idx, bid in enumerate(self._ids):
            col = idx % cols
            row = idx // cols
            x   = P + col * step
            y   = P + row * step
            bd  = self._badges[bid]

            tag = f"b{bid}"
            if bd.is_new:
                # New badges: blue placeholder box with "NEW" label
                src = bd.new_small
                try:
                    img    = Image.open(src).convert("RGBA").resize((T, T), Image.LANCZOS)
                    tk_img = ImageTk.PhotoImage(img)
                    self._thumbs.append(tk_img)
                    self._cv.create_image(x, y, anchor="nw", image=tk_img, tags=tag)
                except Exception:
                    self._thumbs.append(None)
                    self._cv.create_rectangle(x, y, x + T, y + T,
                                               fill="#0f3460", outline="#00aaff", tags=tag)
                    self._cv.create_text(x + T // 2, y + T // 2, text="NEW",
                                          font=("Consolas", 7, "bold"), fill="#00aaff", tags=tag)
                # Blue corner = new
                self._cv.create_rectangle(x, y, x + 8, y + 8,
                                           fill="#00aaff", outline="", tags=tag)
            else:
                src = bd.custom_path or bd.small_path
                try:
                    img    = Image.open(src).convert("RGBA").resize((T, T), Image.LANCZOS)
                    tk_img = ImageTk.PhotoImage(img)
                    self._thumbs.append(tk_img)
                    self._cv.create_image(x, y, anchor="nw", image=tk_img, tags=tag)
                except Exception:
                    self._thumbs.append(None)
                    self._cv.create_rectangle(x, y, x + T, y + T, fill="#333", tags=tag)
                # Green corner = replaced
                if bd.custom_path:
                    self._cv.create_rectangle(x + T - 6, y, x + T, y + 6,
                                               fill="#00ff88", outline="", tags=tag)

            # Selection highlight
            if bid == self._sel_id:
                self._cv.create_rectangle(x - 1, y - 1, x + T + 1, y + T + 1,
                                           outline=ACC, width=2, tags=tag)

        rows = (len(self._ids) + cols - 1) // cols
        self._cv.configure(scrollregion=(0, 0, cols * step + P, rows * step + P))

    def _on_click(self, event):
        T, P = self.THUMB, self.PAD
        step = T + P
        cx = self._cv.canvasx(event.x)
        cy = self._cv.canvasy(event.y)
        col = int(cx // step)
        row = int(cy // step)
        idx = row * self._cols + col
        if 0 <= idx < len(self._ids):
            self._select(self._ids[idx])

    def _select(self, bid: int):
        self._sel_id = bid
        bd = self._badges[bid]
        if bd.is_new:
            src = bd.new_large or bd.new_small
            status = (f"New badge — small: {os.path.basename(bd.new_small or '')}"
                      + (f"\nLarge: {os.path.basename(bd.new_large)}" if bd.new_large else "\n(large auto-derived from small)"))
            lbl_color = "#00aaff"
        else:
            src = bd.custom_path or bd.large_path or bd.small_path
            if bd.custom_path:
                status = f"Custom: {os.path.basename(bd.custom_path)} ✓"
                lbl_color = "#4caf50"
            else:
                status = "Original (unmodified)"
                lbl_color = "#666"
        try:
            img = Image.open(src).convert("RGBA")
            img.thumbnail((220, 220), Image.LANCZOS)
            tk_img = ImageTk.PhotoImage(img)
            self._prev_tk = tk_img
            self._prev_cv.delete("all")
            self._prev_cv.create_image(110, 110, anchor="center", image=tk_img)
        except Exception:
            self._prev_cv.delete("all")
        tag = " [NEW]" if bd.is_new else ""
        self._sel_lbl.config(text=f"Badge ID: {bid}{tag}")
        self._custom_lbl.config(text=status, foreground=lbl_color)
        self._draw_grid()

    # ── Add new badge ──────────────────────────────────────────────────────────

    def _add_badge_dialog(self):
        dlg = tk.Toplevel(self, bg=BG)
        dlg.title("Add New Badge")
        dlg.resizable(False, False)
        dlg.grab_set()

        ttk.Label(dlg, text="Add New Badge", font=("Segoe UI", 11, "bold"),
                  foreground=ACC).grid(row=0, column=0, columnspan=3,
                                       sticky="w", padx=12, pady=(12, 6))

        # Badge ID
        ttk.Label(dlg, text="Badge ID:").grid(row=1, column=0, sticky="w", padx=12, pady=4)
        # Suggest next ID: first gap, or swf_count+1 if no gaps
        suggest = self._gaps[0] if self._gaps else self._swf_count + 1
        bid_var = tk.StringVar(value=str(suggest))
        bid_ent = ttk.Entry(dlg, textvariable=bid_var, width=8)
        bid_ent.grid(row=1, column=1, sticky="w", padx=4)

        # Gap hint
        if self._gaps:
            hint = f"Suggested gap slots (no script change needed): {', '.join(str(g) for g in self._gaps[:8])}{'…' if len(self._gaps) > 8 else ''}"
        else:
            hint = f"No gaps — IDs > {self._swf_count} require script count update (handled automatically)"
        ttk.Label(dlg, text=hint, foreground="#555",
                  font=("Segoe UI", 8), wraplength=380).grid(
            row=2, column=0, columnspan=3, sticky="w", padx=12, pady=(0, 8))

        # Small image
        small_var = tk.StringVar()
        ttk.Label(dlg, text="Small image:").grid(row=3, column=0, sticky="w", padx=12, pady=4)
        small_ent = ttk.Entry(dlg, textvariable=small_var, width=32)
        small_ent.grid(row=3, column=1, padx=4)
        ttk.Button(dlg, text="Browse…",
                   command=lambda: small_var.set(
                       filedialog.askopenfilename(title="Small badge image",
                           filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp"), ("All", "*.*")])
                       or small_var.get())).grid(row=3, column=2, padx=(0, 12))

        # Large image
        large_var = tk.StringVar()
        ttk.Label(dlg, text="Large image:").grid(row=4, column=0, sticky="w", padx=12, pady=4)
        large_ent = ttk.Entry(dlg, textvariable=large_var, width=32)
        large_ent.grid(row=4, column=1, padx=4)
        ttk.Button(dlg, text="Browse…",
                   command=lambda: large_var.set(
                       filedialog.askopenfilename(title="Large badge image (optional)",
                           filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp"), ("All", "*.*")])
                       or large_var.get())).grid(row=4, column=2, padx=(0, 12))
        ttk.Label(dlg, text="(leave blank to auto-scale from small)",
                  foreground="#555", font=("Segoe UI", 8)).grid(
            row=5, column=1, columnspan=2, sticky="w", padx=4, pady=(0, 8))

        err_lbl = ttk.Label(dlg, text="", foreground="#e94560")
        err_lbl.grid(row=6, column=0, columnspan=3, padx=12)

        def _ok():
            try:
                bid = int(bid_var.get().strip())
            except ValueError:
                err_lbl.config(text="Badge ID must be a number.")
                return
            if bid in self._badges:
                err_lbl.config(text=f"Badge ID {bid} already exists.")
                return
            sp = small_var.get().strip()
            if not sp or not os.path.exists(sp):
                err_lbl.config(text="Select a valid small image.")
                return
            lp = large_var.get().strip() or None
            if lp and not os.path.exists(lp):
                err_lbl.config(text="Large image path not found.")
                return
            bd = BadgeData(badge_id=bid, small_char=None, small_path=None,
                           is_new=True, new_small=sp, new_large=lp)
            self._badges[bid] = bd
            self._ids = sorted(self._badges)
            if bid in self._gaps:
                self._gaps.remove(bid)
            self._save_btn.config(state="normal")
            self._status.config(
                text=f"{len([b for b in self._badges.values() if b.is_new])} new badge(s) queued for save.",
                foreground="#00aaff")
            dlg.destroy()
            self._select(bid)

        btn_row = ttk.Frame(dlg)
        btn_row.grid(row=7, column=0, columnspan=3, pady=(4, 12), padx=12, sticky="e")
        ttk.Button(btn_row, text="Cancel", command=dlg.destroy).pack(side="left", padx=(0, 8))
        ttk.Button(btn_row, text="Add Badge", style="Accent.TButton",
                   command=_ok).pack(side="left")

        dlg.columnconfigure(1, weight=1)

    # ── Export ─────────────────────────────────────────────────────────────────

    def _export(self):
        if self._sel_id is None:
            messagebox.showwarning("No selection", "Click a badge first.")
            return
        bd = self._sel_id
        data = self._badges[bd]
        # Prefer large, fall back to small; use custom if set
        src = data.custom_path or data.large_path or data.small_path
        if data.is_new:
            src = data.new_large or data.new_small
        if not src or not os.path.exists(src):
            messagebox.showwarning("Not available", "No image to export for this badge.")
            return
        ext  = os.path.splitext(src)[1] or ".png"
        dest = filedialog.asksaveasfilename(
            title="Export badge image",
            defaultextension=ext,
            initialfile=f"badge_{bd}{ext}",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("All files", "*.*")])
        if not dest:
            return
        # Convert to PNG/JPEG as chosen by the user's extension
        try:
            img = Image.open(src).convert("RGBA")
            if dest.lower().endswith((".jpg", ".jpeg")):
                img = img.convert("RGB")
            img.save(dest)
            messagebox.showinfo("Exported", f"Badge {bd} saved to:\n{dest}")
        except Exception as e:
            messagebox.showerror("Export failed", str(e))

    # ── Replace / clear ────────────────────────────────────────────────────────

    def _replace(self):
        if self._sel_id is None:
            messagebox.showwarning("No selection", "Click a badge first.")
            return
        path = filedialog.askopenfilename(
            title="Select replacement image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.gif"), ("All", "*.*")])
        if not path:
            return
        self._badges[self._sel_id].custom_path = path
        self._select(self._sel_id)
        self._save_btn.config(state="normal")

    def _clear(self):
        if self._sel_id is None:
            return
        self._badges[self._sel_id].custom_path = None
        self._select(self._sel_id)
        if not any(bd.custom_path for bd in self._badges.values()):
            self._save_btn.config(state="disabled")

    # ── Save ───────────────────────────────────────────────────────────────────

    def _save(self):
        modified = {bid: bd for bid, bd in self._badges.items()
                    if bd.custom_path or bd.is_new}
        if not modified:
            return
        self._status.config(text="Saving…", foreground="#aaa")
        self._save_btn.config(state="disabled")
        self.update()
        threading.Thread(target=self._save_worker, args=(modified,), daemon=True).start()

    def _save_worker(self, modified: dict[int, BadgeData]):
        badges_swf = os.path.join(CACHE_DIR, "badges", "badges.swf")
        tmp1 = os.path.join(self._tmp, "badges_step1.swf")
        tmp2 = os.path.join(self._tmp, "badges_step2.swf")

        replacements = {bd: bd for bd in modified.values() if not bd.is_new}
        new_badges   = [bd for bd in modified.values() if bd.is_new]

        current = badges_swf

        # Step 1: replace existing badge images via FFDec
        rep_map: dict[int, str] = {}
        for bd in replacements:
            rep_map[bd.small_char] = self._prep(bd.custom_path, bd.small_path, bd.badge_id, "s")
            if bd.large_char and bd.large_path:
                rep_map[bd.large_char] = self._prep(bd.custom_path, bd.large_path, bd.badge_id, "l")

        if rep_map:
            ok = replace_all_images_in_swf(current, rep_map, tmp1)
            if not ok:
                self.after(0, lambda: [
                    self._status.config(text="⚠ Replace step failed.", foreground="#e94560"),
                    self._save_btn.config(state="normal")])
                return
            current = tmp1

        # Step 2: inject new badge bitmaps directly into the SWF
        if new_badges:
            inject_list = []
            for bd in new_badges:
                small_img = Image.open(bd.new_small).convert("RGBA")
                # Default small size ~30x30, large ~80x80
                small_img = small_img.resize(
                    self._target_size(bd.new_small, (30, 30)), Image.LANCZOS)
                large_img = (Image.open(bd.new_large).convert("RGBA")
                             if bd.new_large else small_img.resize((80, 80), Image.LANCZOS))
                inject_list.append({'badge_id': bd.badge_id,
                                    'small': small_img, 'large': large_img})
            ok = add_badges_to_swf(current, inject_list, tmp2)
            if not ok:
                self.after(0, lambda: [
                    self._status.config(text="⚠ Badge inject failed.", foreground="#e94560"),
                    self._save_btn.config(state="normal")])
                return
            current = tmp2

        shutil.copy2(current, badges_swf)
        n_rep = len(rep_map) // 2 if rep_map else 0  # each badge has 2 slots
        n_new = len(new_badges)
        msg = f"✓ Saved: {n_rep} replaced, {n_new} new badge(s) → cache/badges/badges.swf"
        # Mark new badges as no longer "new" now they're in the SWF
        for bd in new_badges:
            bd.is_new = False
        self.after(0, lambda: [
            self._status.config(text=msg, foreground="#4caf50"),
            self._save_btn.config(state="normal")])

    def _target_size(self, img_path: str, fallback: tuple) -> tuple:
        """Return (W, H) of the original image, capped to reasonable badge size."""
        try:
            w, h = Image.open(img_path).size
            return (min(w, 60), min(h, 60))
        except Exception:
            return fallback

    def _prep(self, custom: str, orig: str, bid: int, size: str) -> str:
        """Resize custom image to match original dims and save as temp PNG."""
        W, H = Image.open(orig).size
        out  = os.path.join(self._tmp, f"brep_{bid}_{size}.png")
        Image.open(custom).convert("RGBA").resize((W, H), Image.LANCZOS).save(out, "PNG")
        return out


# ── Main application ───────────────────────────────────────────────────────────

class CarModderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"1320 Legends Car Modder v{VERSION}  ·  Open1320Legends.com")
        self.resizable(True, True)
        self.configure(bg=BG)
        self.minsize(1200, 720)

        self._tmp      = tempfile.mkdtemp(prefix="carmod_")
        self._cfg      = _load_config()
        self._pkg_info: dict = {}
        self._slots: list[ImageSlot] = []
        self._sel: ImageSlot|None = None
        self._decal_groups: dict[str, list] = {}
        self._tk_orig = self._tk_mod = None

        # Wheel position vars: (view, tire) → {var_name: DoubleVar}
        # view = 'f' or 'b', tire = 'F' (front), 'R' (rear), 'Back' (far-side race wheel, b only)
        self._wheel_vars: dict[tuple, dict[str, tk.DoubleVar]] = {
            ('f', 'F'): {'tx': tk.DoubleVar(value=284), 'ty': tk.DoubleVar(value=174),
                         'scx': tk.DoubleVar(value=100), 'scy': tk.DoubleVar(value=100)},
            ('f', 'R'): {'tx': tk.DoubleVar(value=514), 'ty': tk.DoubleVar(value=149),
                         'scx': tk.DoubleVar(value=100), 'scy': tk.DoubleVar(value=100)},
            ('b', 'F'): {'tx': tk.DoubleVar(value=66),  'ty': tk.DoubleVar(value=221),
                         'scx': tk.DoubleVar(value=100), 'scy': tk.DoubleVar(value=100)},
            ('b', 'R'): {'tx': tk.DoubleVar(value=152), 'ty': tk.DoubleVar(value=177),
                         'scx': tk.DoubleVar(value=100), 'scy': tk.DoubleVar(value=100)},
            ('b', 'Back'): {'tx': tk.DoubleVar(value=435), 'ty': tk.DoubleVar(value=164),
                            'scx': tk.DoubleVar(value=100), 'scy': tk.DoubleVar(value=100)},
        }
        self._wheel_src: dict[tuple, dict] = {}  # original values from source car
        # Plate corner points (p1-p4), back-view only
        self._plate_vars: dict[str, dict[str, tk.DoubleVar]] = {
            'p1': {'tx': tk.DoubleVar(value=451), 'ty': tk.DoubleVar(value=231)},
            'p2': {'tx': tk.DoubleVar(value=538), 'ty': tk.DoubleVar(value=234)},
            'p3': {'tx': tk.DoubleVar(value=542), 'ty': tk.DoubleVar(value=272)},
            'p4': {'tx': tk.DoubleVar(value=455), 'ty': tk.DoubleVar(value=272)},
        }
        self._plate_src: dict[str, dict] = {}  # original values from source car

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._setup_ffdec()             # configure FFDec path before any SWF work
        self.after(200, self._refresh_car_list)

    # ── FFDec setup ────────────────────────────────────────────────────────────

    def _setup_ffdec(self):
        path = self._cfg.get("ffdec_path", "")
        if path and os.path.exists(path):
            set_ffdec_path(path)
            self._ffdec_lbl.config(text=f"FFDec: {os.path.basename(os.path.dirname(path))}",
                                    foreground="#4caf50")
            return
        auto = find_ffdec_default()
        if auto:
            set_ffdec_path(auto)
            self._cfg["ffdec_path"] = auto
            _save_config(self._cfg)
            self._ffdec_lbl.config(text=f"FFDec: {os.path.basename(os.path.dirname(auto))}",
                                    foreground="#4caf50")
            return
        # Not found — prompt
        self._ffdec_lbl.config(text="FFDec: not found", foreground="#e94560")
        self.after(300, self._prompt_ffdec)

    def _prompt_ffdec(self):
        messagebox.showinfo(
            "Locate FFDec",
            "JPEXS Free Flash Decompiler (ffdec.bat) was not found.\n\n"
            "Please locate ffdec.bat to enable SWF editing.")
        self._locate_ffdec()

    def _locate_ffdec(self):
        path = filedialog.askopenfilename(
            title="Locate ffdec.bat",
            filetypes=[("FFDec launcher", "ffdec.bat"), ("All files", "*.*")])
        if path and os.path.exists(path):
            set_ffdec_path(path)
            self._cfg["ffdec_path"] = path
            _save_config(self._cfg)
            self._ffdec_lbl.config(
                text=f"FFDec: {os.path.basename(os.path.dirname(path))}",
                foreground="#4caf50")
            messagebox.showinfo("FFDec Configured", f"FFDec set to:\n{path}")
        else:
            self._ffdec_lbl.config(text="FFDec: not configured", foreground="#e94560")

    # ── Style ──────────────────────────────────────────────────────────────────

    def _style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure(".",            background=BG, foreground=FG, font=("Segoe UI",9))
        s.configure("TLabel",       background=BG, foreground=FG)
        s.configure("TFrame",       background=BG)
        s.configure("TNotebook",    background=BG, tabmargins=[2, 5, 2, 0])
        s.configure("TNotebook.Tab", background="#0f3460", foreground=FG, padding=[12, 4])
        s.map("TNotebook.Tab",      background=[("selected", BG)],
                                    foreground=[("selected", ACC)])
        s.configure("TLabelframe",  background=BG, foreground=ACC)
        s.configure("TLabelframe.Label", background=BG, foreground=ACC,
                     font=("Segoe UI",9,"bold"))
        s.configure("TButton",      background="#0f3460", foreground=FG,
                     relief="flat", padding=5)
        s.map("TButton",            background=[("active","#16213e")])
        s.configure("Accent.TButton", background=ACC, foreground=DARK,
                     font=("Segoe UI",9,"bold"))
        s.map("Accent.TButton",     background=[("active","#00aad4")])
        s.configure("Warn.TButton", background="#e94560", foreground="white",
                     font=("Segoe UI",10,"bold"), padding=8)
        s.map("Warn.TButton",       background=[("active","#c73652")])
        s.configure("TCombobox",    fieldbackground="#16213e", foreground=FG)
        s.configure("TEntry",       fieldbackground="#16213e", foreground=FG)
        s.configure("TCheckbutton", background=BG, foreground=FG)
        s.configure("Horizontal.TScale", background=BG, troughcolor="#16213e")
        s.configure("TSpinbox",     fieldbackground="#16213e", foreground=FG)

    # ── UI ─────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self._style()
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        nb = ttk.Notebook(self)
        nb.grid(row=0, column=0, sticky="nsew")

        car_tab = ttk.Frame(nb)
        nb.add(car_tab, text="  Car Modder  ")
        self._build_car_tab(car_tab)

        paint_tab = ttk.Frame(nb)
        nb.add(paint_tab, text="  Paint Lab  ")
        paint_tab.columnconfigure(0, weight=1)
        paint_tab.rowconfigure(0, weight=1)
        self._paint_lab = PaintLabFrame(
            paint_tab,
            get_slots    = lambda: list(self._slots),
            get_pkg_info = lambda: self._pkg_info,
            get_src_id   = lambda: self._src_var.get(),
            tmp_dir      = self._tmp,
        )
        self._paint_lab.grid(row=0, column=0, sticky="nsew")

        rim_tab = ttk.Frame(nb, padding=4)
        nb.add(rim_tab, text="  Rim Editor  ")
        rim_tab.columnconfigure(0, weight=1)
        rim_tab.rowconfigure(0, weight=1)
        self._rim_editor = RimEditorFrame(rim_tab, self._tmp)
        self._rim_editor.grid(row=0, column=0, sticky="nsew")

        badge_tab = ttk.Frame(nb, padding=8)
        nb.add(badge_tab, text="  Badge Editor  ")
        badge_tab.columnconfigure(0, weight=1)
        badge_tab.rowconfigure(0, weight=1)
        self._badge_editor = BadgeEditorFrame(badge_tab, self._tmp)
        self._badge_editor.grid(row=0, column=0, sticky="nsew")

        # Path info strip
        info = ttk.Frame(self)
        info.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 0))
        ttk.Label(info,
                   text=f"Game: {GAME_DIR}   |   Cache: {CACHE_DIR}   |   "
                        f"Packages: {PACKAGES_DIR}",
                   foreground="#444", font=("Segoe UI",7)).pack(side="left", anchor="w")
        ttk.Button(info, text="Change FFDec…", width=14,
                   command=self._locate_ffdec).pack(side="right", padx=(4, 0))
        self._ffdec_lbl = ttk.Label(info, text="FFDec: checking…",
                                     foreground="#aaa", font=("Segoe UI", 7))
        self._ffdec_lbl.pack(side="right")

        # Branding footer
        brand = ttk.Frame(self)
        brand.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 4))
        ttk.Label(brand,
                   text="Created by Trai  ·  Open1320Legends.com  ·  OblongGangGang",
                   foreground="#555", font=("Segoe UI",8,"italic")).pack(anchor="e")

    def _build_car_tab(self, tab):
        tab.columnconfigure(0, weight=0)
        tab.columnconfigure(1, weight=1)
        tab.rowconfigure(0, weight=1)

        # ── LEFT SIDEBAR ──────────────────────────────────────────────────────
        left = ttk.Frame(tab, padding=(8,8,4,8))
        left.grid(row=0, column=0, sticky="nsew")
        left.rowconfigure(1, weight=1)

        # Car selector
        car_lf = ttk.LabelFrame(left, text="Source Car", padding=6)
        car_lf.grid(row=0, column=0, sticky="ew", pady=(0,6))
        car_lf.columnconfigure(0, weight=1)

        self._src_var = tk.StringVar()
        self._src_combo = ttk.Combobox(car_lf, textvariable=self._src_var,
                                        width=30, state="readonly")
        self._src_combo.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0,4))

        btn_row = ttk.Frame(car_lf)
        btn_row.grid(row=1, column=0, columnspan=2, sticky="ew")
        ttk.Button(btn_row, text="Load Car →", style="Accent.TButton",
                    command=self._load_car).pack(side="left", fill="x", expand=True, padx=(0,4))
        ttk.Button(btn_row, text="↺", width=3,
                    command=self._refresh_car_list).pack(side="left")

        self._car_status = ttk.Label(car_lf, text="", foreground="#aaa", wraplength=240)
        self._car_status.grid(row=2, column=0, columnspan=2, sticky="w", pady=(4,0))

        self._load_progress = ttk.Progressbar(car_lf, mode='determinate',
                                               maximum=100, length=240)
        self._load_progress.grid(row=3, column=0, columnspan=2, sticky="ew",
                                  pady=(2, 0))
        self._load_progress.grid_remove()   # hidden until loading starts

        # Part list
        parts_lf = ttk.LabelFrame(left, text="Part Images", padding=6)
        parts_lf.grid(row=1, column=0, sticky="nsew", pady=(0,6))
        parts_lf.rowconfigure(0, weight=1)
        parts_lf.columnconfigure(0, weight=1)

        self._lb = tk.Listbox(parts_lf, bg=DARK, fg=FG, selectbackground="#0f3460",
                               relief="flat", font=("Consolas",8), width=32,
                               activestyle="none")
        self._lb.grid(row=0, column=0, sticky="nsew")
        sb = ttk.Scrollbar(parts_lf, command=self._lb.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self._lb.configure(yscrollcommand=sb.set)
        self._lb.bind("<<ListboxSelect>>", self._on_select)

        # Export
        exp_lf = ttk.LabelFrame(left, text="Bulk Export", padding=6)
        exp_lf.grid(row=2, column=0, sticky="ew", pady=(0,6))
        ttk.Button(exp_lf, text="Export All Images to Folder…",
                    command=self._export_all).pack(fill="x")
        ttk.Button(exp_lf, text="Parts Catalogue…",
                    command=lambda: PartsCatalogueDialog(self)).pack(fill="x", pady=(4, 0))

        # Build
        build_lf = ttk.LabelFrame(left, text="Build New Car", padding=6)
        build_lf.grid(row=3, column=0, sticky="ew")
        build_lf.columnconfigure(1, weight=1)

        ttk.Label(build_lf, text="Car ID:").grid(row=0, column=0, sticky="w", padx=(0,4))
        self._new_id = tk.StringVar(value="161")
        ttk.Entry(build_lf, textvariable=self._new_id, width=7).grid(row=0, column=1, sticky="w")

        ttk.Label(build_lf, text="Name:").grid(row=1, column=0, sticky="w", pady=(4,0))
        self._new_name = tk.StringVar(value="Hellion Mustang Black")
        ttk.Entry(build_lf, textvariable=self._new_name).grid(row=1, column=1,
                                                                sticky="ew", pady=(4,0))

        self._copy_cache = tk.BooleanVar(value=True)
        ttk.Checkbutton(build_lf, text="Copy to game cache",
                         variable=self._copy_cache).grid(row=2, column=0, columnspan=2,
                                                          sticky="w", pady=(4,0))

        # ── Color lock (row 3) ─────────────────────────────────────────────────
        self._lock_color     = tk.BooleanVar(value=False)
        self._lock_color_rgb = (200, 30, 30)
        color_fr = ttk.Frame(build_lf)
        color_fr.grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))
        ttk.Checkbutton(color_fr, text="Lock color (solid, no in-game repaint)",
                        variable=self._lock_color).pack(side="left")
        self._color_swatch = tk.Button(
            color_fr, bg="#c81e1e", width=2, height=1, relief="solid",
            command=self._pick_lock_color)
        self._color_swatch.pack(side="left", padx=(6, 0))

        ttk.Button(build_lf, text="Clone & Build Car",
                    style="Warn.TButton",
                    command=self._build_car).grid(row=4, column=0, columnspan=2,
                                                   sticky="ew", pady=(6,0))

        self._build_status = ttk.Label(build_lf, text="", foreground="#aaa", wraplength=240)
        self._build_status.grid(row=5, column=0, columnspan=2, sticky="w", pady=(4,0))

        ttk.Separator(build_lf, orient="horizontal").grid(
            row=6, column=0, columnspan=2, sticky="ew", pady=(8, 4))
        ttk.Label(build_lf, text="Upload to Server",
                  font=("Segoe UI", 8, "bold"), foreground=ACC).grid(
            row=7, column=0, columnspan=2, sticky="w")

        ttk.Label(build_lf, text="Author:").grid(row=8, column=0, sticky="w", pady=(4,0))
        self._upload_author = tk.StringVar(value="")
        ttk.Entry(build_lf, textvariable=self._upload_author).grid(
            row=8, column=1, sticky="ew", pady=(4,0))

        ttk.Label(build_lf, text="Description:").grid(row=9, column=0, sticky="w", pady=(2,0))
        self._upload_desc = tk.StringVar(value="")
        ttk.Entry(build_lf, textvariable=self._upload_desc).grid(
            row=9, column=1, sticky="ew", pady=(2,0))

        ttk.Label(build_lf, text="API Key:").grid(row=10, column=0, sticky="w", pady=(2,0))
        self._upload_key = tk.StringVar(value="")
        ttk.Entry(build_lf, textvariable=self._upload_key, show="*").grid(
            row=10, column=1, sticky="ew", pady=(2,0))

        pub_fr = ttk.Frame(build_lf)
        pub_fr.grid(row=11, column=0, columnspan=2, sticky="w", pady=(6, 0))
        self._upload_public = tk.BooleanVar(value=False)
        ttk.Checkbutton(pub_fr, text="Make public in installer",
                         variable=self._upload_public).pack(side="left")

        ttk.Button(build_lf, text="Upload to nitto.lol",
                    command=self._upload_to_server).grid(
            row=12, column=0, columnspan=2, sticky="ew", pady=(4, 0))

        self._upload_status = ttk.Label(build_lf, text="", foreground="#aaa",
                                         font=("Segoe UI", 8), wraplength=240)
        self._upload_status.grid(row=13, column=0, columnspan=2, sticky="w", pady=(2,0))

        # ── Wheel Aligner ──────────────────────────────────────────────────────
        ttk.Separator(build_lf, orient="horizontal").grid(
            row=14, column=0, columnspan=2, sticky="ew", pady=(8, 4))
        ttk.Button(build_lf, text="Tire / Wheel Aligner…", style="Accent.TButton",
                   command=self._open_wheel_preview).grid(
            row=15, column=0, columnspan=2, sticky="ew", pady=(0, 4))

        # ── MAIN PANEL ────────────────────────────────────────────────────────
        main = ttk.Frame(tab, padding=(4,8,8,8))
        main.grid(row=0, column=1, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        # Original canvas
        orig_lf = ttk.LabelFrame(main, text="Original Image", padding=4)
        orig_lf.grid(row=0, column=0, sticky="nsew", padx=(0,4))
        orig_lf.rowconfigure(0, weight=1); orig_lf.columnconfigure(0, weight=1)
        self._c_orig = tk.Canvas(orig_lf, bg=DARK, highlightthickness=0)
        self._c_orig.grid(row=0, column=0, sticky="nsew")
        self._orig_info = ttk.Label(orig_lf, text="", foreground="#666",
                                     font=("Consolas",7))
        self._orig_info.grid(row=1, column=0, sticky="w")

        # Modified canvas
        mod_lf = ttk.LabelFrame(main, text="Modified Preview", padding=4)
        mod_lf.grid(row=0, column=1, sticky="nsew")
        mod_lf.rowconfigure(0, weight=1); mod_lf.columnconfigure(0, weight=1)
        self._c_mod = tk.Canvas(mod_lf, bg=DARK, highlightthickness=0)
        self._c_mod.grid(row=0, column=0, sticky="nsew")
        self._mod_info = ttk.Label(mod_lf, text="", foreground="#666", font=("Consolas",7))
        self._mod_info.grid(row=1, column=0, sticky="w")

        # ── EDIT PANEL (below canvases) ────────────────────────────────────────
        edit = ttk.Frame(main)
        edit.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8,0))
        edit.columnconfigure(1, weight=1)

        # Part label
        self._part_label = ttk.Label(edit, text="No part selected",
                                      foreground=ACC, font=("Segoe UI",9,"bold"))
        self._part_label.grid(row=0, column=0, columnspan=6, sticky="w", pady=(0,6))

        # ── Color sliders (per-slot) ───────────────────────────────────────────
        slider_lf = ttk.LabelFrame(edit, text="Color Adjust (this image only)", padding=6)
        slider_lf.grid(row=1, column=0, sticky="ew", padx=(0,8))
        slider_lf.columnconfigure(1, weight=1)

        # Preset row
        prow = ttk.Frame(slider_lf)
        prow.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0,6))
        ttk.Label(prow, text="Preset:").pack(side="left", padx=(0,4))
        self._preset_var = tk.StringVar(value="Black")
        pc = ttk.Combobox(prow, textvariable=self._preset_var,
                           values=list(COLOR_PRESETS), width=11, state="readonly")
        pc.pack(side="left")
        pc.bind("<<ComboboxSelected>>", self._apply_preset_to_slot)
        ttk.Button(prow, text="Reset", command=self._reset_slot).pack(side="left", padx=(6,0))
        ttk.Button(prow, text="Apply to ALL parts", command=self._apply_to_all).pack(
            side="left", padx=(12,0))

        self._hue = tk.DoubleVar(value=0)
        self._sat = tk.DoubleVar(value=0.0)
        self._bri = tk.DoubleVar(value=0.12)
        self._slider_enabled = True  # prevent feedback loop when loading slot values

        self._make_slider(slider_lf, 1, "Hue Shift", self._hue, -180, 180, " °", 1)
        self._make_slider(slider_lf, 2, "Saturation", self._sat, 0, 2.0, "x", 0.01)
        self._make_slider(slider_lf, 3, "Brightness", self._bri, 0, 3.0, "x", 0.01)

        # ── Custom image panel ─────────────────────────────────────────────────
        custom_lf = ttk.LabelFrame(edit, text="Custom Image Override", padding=6)
        custom_lf.grid(row=1, column=1, sticky="nsew")
        custom_lf.columnconfigure(0, weight=1)

        self._custom_label = ttk.Label(custom_lf, text="No custom image set.",
                                        foreground="#666", wraplength=300)
        self._custom_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0,6))

        ttk.Button(custom_lf, text="Upload New Image…",
                    style="Accent.TButton",
                    command=self._upload_image).grid(row=1, column=0, sticky="ew", padx=(0,4))
        ttk.Button(custom_lf, text="Open Overlay Tool",
                    command=self._open_overlay).grid(row=1, column=1, sticky="ew")

        ttk.Button(custom_lf, text="Align / Transform Existing Part…",
                    command=self._align_existing).grid(row=2, column=0, columnspan=2,
                                                        sticky="ew", pady=(4,0))

        ttk.Button(custom_lf, text="Clear override (revert to original)",
                    command=self._clear_override).grid(row=3, column=0, columnspan=2,
                                                        sticky="ew", pady=(4,0))

        ttk.Label(custom_lf,
                   text="Overlay tool shows original vs new image overlaid so\n"
                        "you can verify positioning before committing.\n"
                        "\"Align Existing\" lets you stretch/skew the current part image\n"
                        "without uploading a new one (useful for shadow tweaks etc.)",
                   foreground="#555", font=("Segoe UI",8)).grid(row=4, column=0,
                                                                  columnspan=2, sticky="w",
                                                                  pady=(6,0))

        # ── Decal Layers panel ────────────────────────────────────────────────
        decal_lf = ttk.LabelFrame(edit, text="Decal Layers", padding=6)
        decal_lf.grid(row=1, column=2, sticky="nsew", padx=(8, 0))
        decal_lf.columnconfigure(0, weight=1)
        edit.columnconfigure(2, weight=1)

        list_fr = ttk.Frame(decal_lf)
        list_fr.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0, 4))
        list_fr.columnconfigure(0, weight=1)
        decal_lf.rowconfigure(0, weight=1)

        self._decal_lb = tk.Listbox(list_fr, bg=DARK, fg=FG, selectbackground="#0f3460",
                                     height=4, font=("Consolas", 8))
        self._decal_lb.grid(row=0, column=0, sticky="nsew")
        self._decal_lb.bind("<<ListboxSelect>>", self._on_decal_select)
        dscroll = ttk.Scrollbar(list_fr, command=self._decal_lb.yview)
        dscroll.grid(row=0, column=1, sticky="ns")
        self._decal_lb.config(yscrollcommand=dscroll.set)

        dbtn_row = ttk.Frame(decal_lf)
        dbtn_row.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        ttk.Button(dbtn_row, text="+ Add", style="Accent.TButton",
                   command=self._add_decal).pack(side="left", padx=(0, 4))
        ttk.Button(dbtn_row, text="Remove",
                   command=self._remove_decal).pack(side="left", padx=(0, 4))
        ttk.Button(dbtn_row, text="↑", width=2,
                   command=lambda: self._move_decal(-1)).pack(side="left", padx=(0, 2))
        ttk.Button(dbtn_row, text="↓", width=2,
                   command=lambda: self._move_decal(1)).pack(side="left")
        ttk.Button(dbtn_row, text="Clear All",
                   command=self._clear_all_decals).pack(side="right")

        ctrl_fr = ttk.LabelFrame(decal_lf, text="Selected Decal", padding=4)
        ctrl_fr.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        ctrl_fr.columnconfigure(1, weight=1); ctrl_fr.columnconfigure(3, weight=1)

        ttk.Label(ctrl_fr, text="X:").grid(row=0, column=0, sticky="w")
        self._decal_x = tk.IntVar(value=0)
        tk.Spinbox(ctrl_fr, textvariable=self._decal_x, from_=-9999, to=9999, increment=1,
                   width=6, bg="#16213e", fg=ACC, buttonbackground="#0f3460", relief="flat",
                   command=self._sync_decal_props).grid(row=0, column=1, sticky="w", padx=(2, 8))
        ttk.Label(ctrl_fr, text="Y:").grid(row=0, column=2, sticky="w")
        self._decal_y = tk.IntVar(value=0)
        tk.Spinbox(ctrl_fr, textvariable=self._decal_y, from_=-9999, to=9999, increment=1,
                   width=6, bg="#16213e", fg=ACC, buttonbackground="#0f3460", relief="flat",
                   command=self._sync_decal_props).grid(row=0, column=3, sticky="w", padx=(2, 0))

        ttk.Label(ctrl_fr, text="Scale:").grid(row=1, column=0, sticky="w", pady=(4, 0))
        self._decal_scale = tk.DoubleVar(value=1.0)
        tk.Spinbox(ctrl_fr, textvariable=self._decal_scale, from_=0.05, to=10.0, increment=0.05,
                   width=6, format="%.2f", bg="#16213e", fg=ACC, buttonbackground="#0f3460",
                   relief="flat", command=self._sync_decal_props).grid(
                   row=1, column=1, sticky="w", padx=(2, 8), pady=(4, 0))
        ttk.Label(ctrl_fr, text="Opacity:").grid(row=1, column=2, sticky="w", pady=(4, 0))
        self._decal_alpha = tk.DoubleVar(value=1.0)
        tk.Spinbox(ctrl_fr, textvariable=self._decal_alpha, from_=0.0, to=1.0, increment=0.05,
                   width=6, format="%.2f", bg="#16213e", fg=ACC, buttonbackground="#0f3460",
                   relief="flat", command=self._sync_decal_props).grid(
                   row=1, column=3, sticky="w", padx=(2, 0), pady=(4, 0))

        grp_fr = ttk.LabelFrame(decal_lf, text="Groups", padding=4)
        grp_fr.grid(row=3, column=0, columnspan=2, sticky="ew")
        grp_fr.columnconfigure(0, weight=1)
        self._group_var = tk.StringVar()
        self._group_combo = ttk.Combobox(grp_fr, textvariable=self._group_var,
                                          width=16, state="readonly")
        self._group_combo.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(grp_fr, text="Load",
                   command=self._load_decal_group).grid(row=0, column=1, padx=(0, 4))
        ttk.Button(grp_fr, text="Save…",
                   command=self._save_decal_group).grid(row=0, column=2)

    def _make_slider(self, parent, row, label, var, from_, to, suffix, res):
        ttk.Label(parent, text=label, width=12).grid(row=row, column=0, sticky="w")
        s = ttk.Scale(parent, variable=var, from_=from_, to=to, orient="horizontal",
                       length=240, command=lambda _: self._on_slider_change())
        s.grid(row=row, column=1, padx=6, sticky="ew")
        lbl = ttk.Label(parent, width=7, anchor="w")
        lbl.grid(row=row, column=2)
        def _upd(*_):
            v = var.get()
            lbl.config(text=f"{v:.{0 if res>=1 else 2}f}{suffix}")
        var.trace_add("write", _upd)
        _upd()

    # ── Car list ───────────────────────────────────────────────────────────────

    def _refresh_car_list(self):
        if not os.path.isdir(PACKAGES_DIR):
            self._car_status.config(
                text=f"⚠ Not found:\n{PACKAGES_DIR}", foreground="#e94560")
            return
        self._pkg_info = get_package_info(PACKAGES_DIR)
        labels = [f"{cid}: {CARS.get(cid,f'Car {cid}')} "
                  f"[{'+ '.join(v.upper() for v in sorted(self._pkg_info[cid]))}]"
                  for cid in sorted(self._pkg_info)]
        self._src_combo["values"] = labels
        default = next((l for l in labels if l.startswith("94:")), labels[0] if labels else "")
        self._src_combo.set(default)
        # Auto-suggest next unused car ID
        if self._pkg_info:
            next_id = max(self._pkg_info) + 1
            self._new_id.set(str(next_id))
        self._car_status.config(
            text=f"{len(self._pkg_info)} cars in packages.", foreground="#4caf50")

    def _get_src_id(self) -> int|None:
        try: return int(self._src_var.get().split(":")[0].strip())
        except: return None

    # ── Load car ───────────────────────────────────────────────────────────────

    def _load_car(self):
        car_id = self._get_src_id()
        if car_id is None:
            messagebox.showerror("Error", "Select a car first.")
            return
        self._slots.clear()
        self._sel = None
        self._lb.delete(0, tk.END)
        self._c_orig.delete("all"); self._c_mod.delete("all")
        self._car_status.config(text="Extracting…", foreground="#aaa")
        threading.Thread(target=self._load_worker, args=(car_id,), daemon=True).start()

    def _load_worker(self, car_id: int):
        info = self._pkg_info.get(car_id, {})
        slots, errors = [], []

        # Pre-count so progress bar is accurate
        swf_list = []
        for view in ("f", "b"):
            if view not in info:
                continue
            for fname in sorted(os.listdir(info[view])):
                fpath = os.path.join(info[view], fname)
                if fname.endswith(".swf") and should_recolor(fpath):
                    swf_list.append((view, fname, fpath))
        logo_swf = os.path.join(CAR_DIR, f"logo_{car_id}.swf")
        has_logo = os.path.exists(logo_swf)
        total = len(swf_list) + (1 if has_logo else 0)

        def _prog(done, label=""):
            pct = int(done / total * 100) if total else 100
            self._load_progress['value'] = pct
            if label:
                self._car_status.config(text=label)

        self.after(0, lambda: (self._load_progress.grid(),
                               self._load_progress.configure(value=0)))

        for i, (view, fname, fpath) in enumerate(swf_list):
            self.after(0, _prog, i, f"Extracting [{view.upper()}] {fname}…")
            exp_dir = os.path.join(self._tmp, f"src_{car_id}_{view}_{fname}")
            images  = export_all_images(fpath, exp_dir)
            if not images:
                errors.append(f"{view.upper()}/{fname}")
                continue
            for char_id, img_path in sorted(images.items()):
                slots.append(ImageSlot(fpath, char_id, img_path,
                                        f"[{view.upper()}] {fname}  #{char_id}"))

        if has_logo:
            self.after(0, _prog, len(swf_list), "Extracting logo…")
            exp_dir = os.path.join(self._tmp, f"src_{car_id}_logo")
            images = export_all_images(logo_swf, exp_dir)
            if images:
                for char_id, img_path in sorted(images.items()):
                    slots.append(ImageSlot(logo_swf, char_id, img_path,
                                           f"[LOGO] thumbnail  #{char_id}"))
            else:
                # Fallback: logo SWF has no extractable image layers
                p = export_image(logo_swf, exp_dir)
                if p:
                    slots.append(ImageSlot(logo_swf, 1, p, "[LOGO] thumbnail"))

        self._slots = slots
        self.after(0, self._finish_load, car_id, slots, errors)

    def _finish_load(self, car_id, slots, errors):
        self._lb.delete(0, tk.END)
        for s in slots:
            self._lb.insert(tk.END, s.label)
        n = len(slots)
        err = f"  ({len(errors)} skipped: {', '.join(errors)})" if errors else ""
        self._load_progress['value'] = 100
        self._load_progress.grid_remove()
        self._car_status.config(
            text=f"✓ {n} image(s) from car {car_id}.{err}", foreground="#4caf50")
        if slots:
            self._lb.selection_set(0)
            self._load_slot(slots[0])
        # Populate wheel position spinboxes from source car
        self._load_wheel_positions(car_id)

    def _load_wheel_positions(self, car_id: int):
        info = self._pkg_info.get(car_id, {})
        self._wheel_src = {}
        for view in ('f', 'b'):
            if view not in info:
                continue
            pkg_dir = info[view]
            tire_files = [('F', 'tireF.swf'), ('R', 'tireR.swf')]
            if view == 'b':
                tire_files.append(('Back', 'tireBack.swf'))
            for tire, fname in tire_files:
                key  = (view, tire)
                path = os.path.join(pkg_dir, fname)
                vals = parse_tire_swf(path) if os.path.exists(path) else {}
                self._wheel_src[key] = vals
                for var_name, dv in self._wheel_vars[key].items():
                    if var_name in vals:
                        dv.set(round(float(vals[var_name]), 2))

        # Load plate corner points (p1-p4) from back-view package if present
        self._plate_src = {}
        b_pkg = info.get('b', '')
        for pt_key in ('p1', 'p2', 'p3', 'p4'):
            path = os.path.join(b_pkg, f"{pt_key}.swf") if b_pkg else ''
            vals = parse_tire_swf(path) if os.path.exists(path) else {}
            self._plate_src[pt_key] = vals
            pv = self._plate_vars.get(pt_key, {})
            for var_name, dv in pv.items():
                if var_name in vals:
                    dv.set(round(float(vals[var_name]), 2))

    def _reset_wheel_positions(self):
        for key, vals in self._wheel_src.items():
            for var_name, dv in self._wheel_vars[key].items():
                if var_name in vals:
                    dv.set(round(float(vals[var_name]), 2))

    def _pick_lock_color(self):
        from tkinter.colorchooser import askcolor
        r, g, b = self._lock_color_rgb
        init = f"#{r:02x}{g:02x}{b:02x}"
        result = askcolor(color=init, title="Choose lock color")
        if result and result[0]:
            r, g, b = (int(c) for c in result[0])
            self._lock_color_rgb = (r, g, b)
            self._color_swatch.configure(bg=f"#{r:02x}{g:02x}{b:02x}")

    def _open_wheel_preview(self):
        if not self._slots:
            messagebox.showinfo("No car loaded", "Load a source car first.")
            return
        car_id = self._get_src_id()
        WheelPreviewWindow(self, self._slots, self._wheel_vars,
                           self._wheel_src, self._pkg_info,
                           car_id, self._tmp,
                           plate_vars=self._plate_vars,
                           plate_src=self._plate_src)

    # ── Slot selection / display ───────────────────────────────────────────────

    def _on_select(self, *_):
        sel = self._lb.curselection()
        if sel and self._slots:
            self._load_slot(self._slots[sel[0]])

    def _load_slot(self, slot: ImageSlot):
        self._sel = slot
        self._part_label.config(text=slot.label +
                                 ("  ★ MODIFIED" if slot.is_modified else ""))
        # Load slot's own color values into sliders (suppress preview redraw during load)
        self._slider_enabled = False
        self._hue.set(slot.hue)
        self._sat.set(slot.sat)
        self._bri.set(slot.bri)
        self._slider_enabled = True

        self._custom_label.config(
            text=f"Custom: {os.path.basename(slot.custom_path)}" if slot.custom_path
            else "No custom image set.", foreground=ACC if slot.custom_path else "#666")

        # Sync decal listbox
        self._refresh_decal_lb()
        if slot.decals:
            self._decal_lb.selection_set(0)
            self._on_decal_select()

        self._draw_orig(slot)
        self._draw_mod(slot)

    def _draw_orig(self, slot: ImageSlot):
        img = slot.orig_image()
        self._c_orig.update_idletasks()
        w = max(self._c_orig.winfo_width(), 100)
        h = max(self._c_orig.winfo_height(), 100)
        thumb = img.copy(); thumb.thumbnail((w, h), Image.LANCZOS)
        self._tk_orig = ImageTk.PhotoImage(thumb)
        self._c_orig.delete("all")
        self._c_orig.create_image(w//2, h//2, image=self._tk_orig, anchor="center")
        self._orig_info.config(text=f"{img.width}×{img.height}px  |  {slot.orig_path}")

    def _draw_mod(self, slot: ImageSlot):
        img = slot.final_image()
        self._c_mod.update_idletasks()
        w = max(self._c_mod.winfo_width(), 100)
        h = max(self._c_mod.winfo_height(), 100)
        thumb = img.copy(); thumb.thumbnail((w, h), Image.LANCZOS)
        self._tk_mod = ImageTk.PhotoImage(thumb)
        self._c_mod.delete("all")
        self._c_mod.create_image(w//2, h//2, image=self._tk_mod, anchor="center")
        src_note = f"  [custom: {os.path.basename(slot.custom_path)}]" if slot.custom_path else ""
        self._mod_info.config(
            text=f"H:{slot.hue:+.0f}° S:{slot.sat:.2f}x B:{slot.bri:.2f}x{src_note}")
        # Refresh list item to show star
        try:
            idx = self._slots.index(slot)
            self._lb.delete(idx)
            self._lb.insert(idx, slot.label + ("  ★" if slot.is_modified else ""))
            self._lb.selection_set(idx)
        except ValueError:
            pass

    # ── Color sliders ──────────────────────────────────────────────────────────

    def _on_slider_change(self):
        if not self._slider_enabled or self._sel is None:
            return
        self._sel.hue = self._hue.get()
        self._sel.sat = self._sat.get()
        self._sel.bri = self._bri.get()
        self._draw_mod(self._sel)

    def _apply_preset_to_slot(self, *_):
        p = self._preset_var.get()
        vals = COLOR_PRESETS.get(p)
        if vals:
            self._hue.set(vals[0]); self._sat.set(vals[1]); self._bri.set(vals[2])
        # _on_slider_change fires automatically via trace

    def _reset_slot(self):
        if self._sel:
            self._hue.set(0); self._sat.set(1.0); self._bri.set(1.0)

    def _apply_to_all(self):
        h, s, b = self._hue.get(), self._sat.get(), self._bri.get()
        for slot in self._slots:
            slot.hue = h; slot.sat = s; slot.bri = b
        # Refresh current display
        if self._sel:
            self._draw_mod(self._sel)
        # Update list stars
        for i, slot in enumerate(self._slots):
            self._lb.delete(i)
            self._lb.insert(i, slot.label + ("  ★" if slot.is_modified else ""))
        if self._sel:
            try:
                idx = self._slots.index(self._sel)
                self._lb.selection_set(idx)
            except ValueError:
                pass
        messagebox.showinfo("Applied", f"H:{h:+.0f}° S:{s:.2f}x B:{b:.2f}x applied "
                                        f"to all {len(self._slots)} parts.")

    # ── Custom image ───────────────────────────────────────────────────────────

    def _upload_image(self):
        slot = self._sel
        if slot is None:
            messagebox.showinfo("Nothing selected", "Click a part in the list first.")
            return
        path = filedialog.askopenfilename(
            title="Choose replacement image",
            filetypes=[("Images","*.png *.jpg *.jpeg *.bmp *.tga *.webp"),
                       ("All files","*.*")])
        if not path:
            return
        slot.custom_path = path
        self._custom_label.config(text=f"Custom: {os.path.basename(path)}",
                                   foreground=ACC)
        self._draw_orig(slot)
        self._draw_mod(slot)
        # Prompt to open overlay
        if messagebox.askyesno("Open Overlay?",
                                "Open the overlay alignment tool to verify positioning?"):
            self._open_overlay()

    def _open_overlay(self):
        slot = self._sel
        if slot is None:
            messagebox.showinfo("Nothing selected", "Select a part first.")
            return
        if slot.custom_path is None:
            messagebox.showinfo("No custom image", "Upload a custom image first.")
            return
        orig = slot.orig_image()
        new  = Image.open(slot.custom_path).convert("RGBA")

        def _accept(baked_img: Image.Image):
            # Save the fully-transformed image (position + scale + skew already baked in)
            baked_path = os.path.join(self._tmp,
                f"baked_{slot.char_id}_{os.path.basename(slot.custom_path)}")
            baked_img.save(baked_path, "PNG")
            slot.custom_path = baked_path
            self._draw_mod(slot)
            self._custom_label.config(
                text=f"Custom: {os.path.basename(baked_path)} ✓", foreground=ACC)

        def _reject():
            slot.custom_path = None
            self._custom_label.config(text="No custom image set.", foreground="#666")
            self._draw_mod(slot)

        OverlayWindow(self, orig, new, _accept, _reject)

    def _align_existing(self):
        """Open overlay aligner using the current slot's own image — no upload needed.
        Lets you stretch/skew/reposition an existing part (shadow, undercarriage, etc.)."""
        slot = self._sel
        if slot is None:
            messagebox.showinfo("Nothing selected", "Select a part first.")
            return
        orig = slot.orig_image()
        # Use the current final image (with any colour/decal adjustments) as the overlay
        current = slot.final_image().copy()

        def _accept(baked_img: Image.Image):
            baked_path = os.path.join(
                self._tmp, f"align_{slot.char_id}_{os.path.basename(slot.swf_path)}.png")
            baked_img.save(baked_path, "PNG")
            slot.custom_path = baked_path
            self._draw_mod(slot)
            self._custom_label.config(
                text=f"Aligned: {os.path.basename(baked_path)} ✓", foreground=ACC)

        def _reject():
            pass  # leave slot unchanged

        OverlayWindow(self, orig, current, _accept, _reject)

    def _clear_override(self):
        if self._sel:
            self._sel.custom_path = None
            self._custom_label.config(text="No custom image set.", foreground="#666")
            self._draw_mod(self._sel)

    # ── Decal methods ──────────────────────────────────────────────────────────

    def _add_decal(self):
        slot = self._sel
        if slot is None:
            messagebox.showwarning("No part selected", "Select a part first.")
            return
        path = filedialog.askopenfilename(
            title="Import decal image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.gif *.webp"), ("All", "*.*")])
        if not path:
            return
        d = {'path': path, 'x': 0, 'y': 0, 'scale': 1.0, 'alpha': 1.0,
             'name': os.path.basename(path)}
        slot.decals.append(d)
        self._refresh_decal_lb()
        self._decal_lb.selection_clear(0, tk.END)
        self._decal_lb.selection_set(len(slot.decals) - 1)
        self._on_decal_select()
        self._draw_mod(slot)

    def _remove_decal(self):
        slot = self._sel
        if not slot:
            return
        sel = self._decal_lb.curselection()
        if not sel:
            return
        idx = sel[0]
        slot.decals.pop(idx)
        self._refresh_decal_lb()
        if slot.decals:
            self._decal_lb.selection_set(min(idx, len(slot.decals) - 1))
            self._on_decal_select()
        self._draw_mod(slot)

    def _move_decal(self, direction: int):
        slot = self._sel
        if not slot:
            return
        sel = self._decal_lb.curselection()
        if not sel:
            return
        idx = sel[0]
        new_idx = idx + direction
        if new_idx < 0 or new_idx >= len(slot.decals):
            return
        slot.decals[idx], slot.decals[new_idx] = slot.decals[new_idx], slot.decals[idx]
        self._refresh_decal_lb()
        self._decal_lb.selection_set(new_idx)
        self._draw_mod(slot)

    def _clear_all_decals(self):
        if self._sel:
            self._sel.decals.clear()
            self._refresh_decal_lb()
            self._draw_mod(self._sel)

    def _on_decal_select(self, *_):
        slot = self._sel
        if not slot:
            return
        sel = self._decal_lb.curselection()
        if not sel:
            return
        d = slot.decals[sel[0]]
        self._decal_x.set(d.get('x', 0))
        self._decal_y.set(d.get('y', 0))
        self._decal_scale.set(d.get('scale', 1.0))
        self._decal_alpha.set(d.get('alpha', 1.0))

    def _sync_decal_props(self, *_):
        slot = self._sel
        if not slot:
            return
        sel = self._decal_lb.curselection()
        if not sel:
            return
        d = slot.decals[sel[0]]
        d['x']     = self._decal_x.get()
        d['y']     = self._decal_y.get()
        d['scale'] = self._decal_scale.get()
        d['alpha'] = self._decal_alpha.get()
        self._draw_mod(slot)

    def _refresh_decal_lb(self):
        slot = self._sel
        self._decal_lb.delete(0, tk.END)
        if not slot:
            return
        for i, d in enumerate(slot.decals):
            self._decal_lb.insert(tk.END,
                f"  {i+1}. {d.get('name', os.path.basename(d['path']))}")

    def _save_decal_group(self):
        if not self._sel or not self._sel.decals:
            messagebox.showinfo("No decals", "Add decals to this part first.")
            return
        name = simpledialog.askstring("Save Group", "Group name:", parent=self)
        if not name:
            return
        self._decal_groups[name] = [dict(d) for d in self._sel.decals]
        self._group_combo['values'] = list(self._decal_groups)
        self._group_var.set(name)

    def _load_decal_group(self):
        slot = self._sel
        if not slot:
            messagebox.showwarning("No part selected", "Select a part first.")
            return
        name = self._group_var.get()
        if not name or name not in self._decal_groups:
            return
        slot.decals = [dict(d) for d in self._decal_groups[name]]
        self._refresh_decal_lb()
        self._draw_mod(slot)

    # ── Export ─────────────────────────────────────────────────────────────────

    def _export_all(self):
        if not self._slots:
            messagebox.showinfo("No car loaded", "Load a car first.")
            return
        folder = filedialog.askdirectory(title="Export images to…",
                                          initialdir=OUTPUT_DIR)
        if not folder:
            return
        os.makedirs(folder, exist_ok=True)
        for slot in self._slots:
            safe = (slot.label.replace("/","_").replace("\\","_").replace(" ","_")
                               .replace("[","").replace("]","").replace("#","c"))
            ext = os.path.splitext(slot.orig_path)[1]
            shutil.copy2(slot.orig_path, os.path.join(folder, f"{safe}_orig{ext}"))
            if slot.is_modified:
                slot.final_image().save(os.path.join(folder, f"{safe}_mod.png"), "PNG")
        messagebox.showinfo("Exported", f"Images saved to:\n{folder}")
        os.startfile(folder)

    # ── Build ──────────────────────────────────────────────────────────────────

    def _build_car(self):
        if not self._slots:
            messagebox.showerror("Error", "Load a source car first.")
            return
        try: new_id = int(self._new_id.get().strip())
        except: messagebox.showerror("Error", "Car ID must be a number."); return
        self._build_status.config(text="Building…")
        threading.Thread(target=self._build_worker, args=(new_id,), daemon=True).start()

    def _build_worker(self, new_id:int):
        def log(msg): self._build_status.config(text=msg)

        car_id  = self._get_src_id()
        out_dir = os.path.join(BASE_DIR, "output")
        copy    = self._copy_cache.get()

        from collections import defaultdict
        by_swf: dict[str,list[ImageSlot]] = defaultdict(list)
        for slot in self._slots:
            by_swf[slot.swf_path].append(slot)

        generated, errors = [], []

        lock_color = self._lock_color.get()

        try:
            for swf_path, swf_slots in by_swf.items():
                fname  = os.path.basename(swf_path)
                parent = os.path.basename(os.path.dirname(swf_path))

                # noPaint.swf controls in-game colour lock — skip it when unlocked;
                # the lock step below will add/remove it explicitly.
                if fname == 'noPaint.swf':
                    continue

                is_logo = fname == f"logo_{car_id}.swf"
                if is_logo:
                    out_swf = os.path.join(out_dir, f"logo_{new_id}.swf")
                    os.makedirs(out_dir, exist_ok=True)
                else:
                    view = "b" if parent.endswith("b") else "f"
                    pkg_out = os.path.join(out_dir, "packages", f"{new_id}{view}")
                    os.makedirs(pkg_out, exist_ok=True)
                    out_swf = os.path.join(pkg_out, fname)

                log(f"Building {fname}…")
                do_tint = lock_color and should_recolor(swf_path)
                replacements = {}
                for slot in swf_slots:
                    final = slot.final_image()
                    if do_tint:
                        final = _paint_tint(final, self._lock_color_rgb)
                    ext   = os.path.splitext(slot.orig_path)[1].lower()
                    tmp   = os.path.join(self._tmp,
                                          f"bld_{new_id}_{fname}_{slot.char_id}{ext}")
                    if ext in (".jpg",".jpeg"):
                        final.convert("RGB").save(tmp, "JPEG", quality=95)
                    else:
                        final.save(tmp, "PNG")
                    replacements[slot.char_id] = tmp

                ok = replace_all_images_in_swf(swf_path, replacements, out_swf)
                if ok: generated.append(out_swf)
                else:  errors.append(fname); log(f"✗ Failed: {fname}")

            # Copy non-visual files (tires, plate etc.) and patch changed values
            info = self._pkg_info.get(car_id, {})
            # Template noPaint.swf from game cache (smallest available)
            _np_template = os.path.join(PACKAGES_DIR, "109f", "noPaint.swf")
            for view in ("f","b"):
                if view not in info: continue
                src_pkg = info[view]
                pkg_out = os.path.join(out_dir, "packages", f"{new_id}{view}")
                os.makedirs(pkg_out, exist_ok=True)

                # ── noPaint.swf: honour the lock-color checkbox ────────────────
                np_out = os.path.join(pkg_out, "noPaint.swf")
                np_src = os.path.join(src_pkg, "noPaint.swf")
                if lock_color:
                    # Ensure noPaint.swf is in output
                    if os.path.exists(np_src):
                        shutil.copy2(np_src, np_out)
                    elif os.path.exists(_np_template):
                        shutil.copy2(_np_template, np_out)
                else:
                    # Ensure noPaint.swf is NOT in output (remove if accidentally written)
                    if os.path.exists(np_out):
                        os.remove(np_out)

                for f in os.listdir(src_pkg):
                    fp = os.path.join(src_pkg, f)
                    if not (f.endswith(".swf") and not should_recolor(fp)):
                        continue
                    if f == 'noPaint.swf':
                        continue  # handled above
                    dst = os.path.join(pkg_out, f)

                    # Tire positioning SWFs
                    tire_key = None
                    if f == "tireF.swf":    tire_key = (view, 'F')
                    elif f == "tireR.swf":  tire_key = (view, 'R')
                    elif f == "tireBack.swf": tire_key = (view, 'Back')

                    if tire_key and tire_key in self._wheel_src:
                        src_vals = self._wheel_src[tire_key]
                        overrides = {}
                        for vn, dv in self._wheel_vars[tire_key].items():
                            new_v = round(dv.get(), 2)
                            old_v = round(float(src_vals.get(vn, new_v)), 2)
                            if new_v != old_v:
                                overrides[vn] = new_v
                        if overrides:
                            log(f"Patching wheel positions in {view.upper()}/{f}: {overrides}")
                            patch_tire_swf(fp, dst, overrides)
                            generated.append(dst)
                            continue

                    # Plate corner SWFs (p1-p4)
                    plate_match = f in ('p1.swf', 'p2.swf', 'p3.swf', 'p4.swf')
                    if plate_match:
                        pt_key = f[:-4]  # 'p1','p2','p3','p4'
                        pv = self._plate_vars.get(pt_key, {})
                        if pv:
                            src_vals = self._plate_src.get(pt_key, {})
                            overrides = {}
                            for vn, dv in pv.items():
                                new_v = round(dv.get(), 2)
                                old_v = round(float(src_vals.get(vn, new_v)), 2)
                                if new_v != old_v:
                                    overrides[vn] = new_v
                            if overrides:
                                log(f"Patching plate {pt_key} in {view.upper()}: {overrides}")
                                patch_tire_swf(fp, dst, overrides)
                                generated.append(dst)
                                continue

                    if not os.path.exists(dst):
                        shutil.copy2(fp, dst)

            # If user edited plate but source car had no p1-p4 SWFs, create them
            # from game template (only for back view where plates live)
            if any(self._plate_vars.get(k) for k in ('p1','p2','p3','p4')):
                _plate_tmpl_dir = os.path.join(PACKAGES_DIR, "116b")
                b_pkg_out = os.path.join(out_dir, "packages", f"{new_id}b")
                b_src_pkg = info.get('b', '')
                os.makedirs(b_pkg_out, exist_ok=True)
                for pt_key in ('p1', 'p2', 'p3', 'p4'):
                    pv = self._plate_vars.get(pt_key, {})
                    if not pv:
                        continue
                    dst = os.path.join(b_pkg_out, f"{pt_key}.swf")
                    if os.path.exists(dst):
                        continue  # already written above
                    src_exists = os.path.join(b_src_pkg, f"{pt_key}.swf") if b_src_pkg else ''
                    tmpl = src_exists if os.path.exists(src_exists) else os.path.join(_plate_tmpl_dir, f"{pt_key}.swf")
                    if not os.path.exists(tmpl):
                        continue
                    overrides = {vn: round(dv.get(), 2) for vn, dv in pv.items()}
                    log(f"Writing plate {pt_key}: {overrides}")
                    patch_tire_swf(tmpl, dst, overrides)
                    generated.append(dst)

            # Copy to game cache
            if copy:
                for fpath in generated:
                    fname  = os.path.basename(fpath)
                    parent = os.path.basename(os.path.dirname(fpath))
                    if fname.startswith("logo_"):
                        shutil.copy2(fpath, os.path.join(CAR_DIR, fname))
                    else:
                        dest_dir = os.path.join(PACKAGES_DIR, parent)
                        os.makedirs(dest_dir, exist_ok=True)
                        shutil.copy2(fpath, os.path.join(dest_dir, fname))
                # Copy non-visual package files to cache
                for view in ("f","b"):
                    pkg_out  = os.path.join(out_dir, "packages", f"{new_id}{view}")
                    dest_dir = os.path.join(PACKAGES_DIR, f"{new_id}{view}")
                    if os.path.isdir(pkg_out):
                        if os.path.exists(dest_dir): shutil.rmtree(dest_dir)
                        shutil.copytree(pkg_out, dest_dir)
                log(f"Copied to cache.")

            n = len(generated)
            err_txt = f"\n⚠ Failed: {', '.join(errors)}" if errors else ""
            log(f"Done! {n} file(s) built for car {new_id}.{err_txt}")
            self.after(0, lambda: messagebox.showinfo(
                "Built",
                f"Car {new_id} ({self._new_name.get()}) complete!\n"
                f"{n} SWF(s) written to:\n{out_dir}"
                + ("\n\nCopied to game cache." if copy else "")
                + (f"\n\n⚠ {err_txt}" if errors else "")))

        except Exception as e:
            import traceback; tb = traceback.format_exc()
            log(f"Error: {e}")
            self.after(0, lambda: messagebox.showerror("Build Error", f"{e}\n\n{tb}"))

    def _upload_to_server(self):
        try:
            new_id = int(self._new_id.get())
        except ValueError:
            messagebox.showerror("Upload", "Set a valid Car ID first.", parent=self)
            return
        api_key = self._upload_key.get().strip()
        if not api_key:
            messagebox.showerror("Upload", "Enter your API key.", parent=self)
            return
        out_dir = os.path.join(BASE_DIR, "output")
        if not os.path.isdir(out_dir):
            messagebox.showerror("Upload",
                                  "No output folder found — build the car first.",
                                  parent=self)
            return
        # Collect files to upload
        files_to_send = []
        logo = os.path.join(out_dir, f"logo_{new_id}.swf")
        if os.path.exists(logo):
            files_to_send.append(("logo", logo, f"logo_{new_id}.swf"))
        for view in ("f", "b"):
            pkg_dir = os.path.join(out_dir, "packages", f"{new_id}{view}")
            if os.path.isdir(pkg_dir):
                for fname in os.listdir(pkg_dir):
                    fp = os.path.join(pkg_dir, fname)
                    if os.path.isfile(fp):
                        files_to_send.append(
                            ("package", fp, f"packages/{new_id}{view}/{fname}"))
        if not files_to_send:
            messagebox.showinfo("Upload",
                                 "No output files found for that car ID.\n"
                                 "Build the car first.", parent=self)
            return
        if not messagebox.askyesno(
                "Confirm upload",
                f"Upload {len(files_to_send)} file(s) for car {new_id} "
                f"({self._new_name.get()}) to nitto.lol?\n\n"
                f"Public: {'YES — will appear in installer' if self._upload_public.get() else 'NO — private/test only'}",
                parent=self):
            return

        self._upload_status.config(text="Uploading…", foreground="#aaa")
        meta = {
            "car_id":      new_id,
            "name":        self._new_name.get(),
            "author":      self._upload_author.get().strip() or "Unknown",
            "description": self._upload_desc.get().strip(),
            "version":     "1.0",
            "public":      self._upload_public.get(),
        }
        threading.Thread(target=self._upload_worker,
                          args=(api_key, meta, files_to_send), daemon=True).start()

    def _upload_worker(self, api_key: str, meta: dict, files: list):
        import urllib.request, urllib.parse, json as _json, mimetypes

        UPLOAD_URL = "http://nitto.lol:8184/mods/upload"
        boundary   = "----NittoModBoundary7a3f9c"
        total      = len(files)

        def _set(msg, color="#aaa"):
            self.after(0, lambda: self._upload_status.config(text=msg, foreground=color))

        try:
            # 1. Upload metadata
            _set("Sending metadata…")
            meta_data  = _json.dumps(meta).encode()
            meta_req   = urllib.request.Request(
                UPLOAD_URL + "/meta",
                data=meta_data,
                headers={
                    "Content-Type":  "application/json",
                    "X-Api-Key":     api_key,
                    "User-Agent":    "1320CarModder/1.0",
                }
            )
            with urllib.request.urlopen(meta_req, timeout=20) as r:
                resp = _json.loads(r.read().decode())
            if not resp.get("ok"):
                _set(f"Error: {resp.get('error','server rejected metadata')}", "#e94560")
                return

            # 2. Upload each file
            for i, (ftype, fpath, rel_path) in enumerate(files, 1):
                _set(f"Uploading {i}/{total}: {os.path.basename(fpath)}…")
                with open(fpath, "rb") as fh:
                    file_data = fh.read()

                body  = (
                    f"--{boundary}\r\n"
                    f'Content-Disposition: form-data; name="car_id"\r\n\r\n'
                    f'{meta["car_id"]}\r\n'
                    f"--{boundary}\r\n"
                    f'Content-Disposition: form-data; name="rel_path"\r\n\r\n'
                    f'{rel_path}\r\n'
                    f"--{boundary}\r\n"
                    f'Content-Disposition: form-data; name="file"; filename="{os.path.basename(fpath)}"\r\n'
                    f'Content-Type: application/octet-stream\r\n\r\n'
                ).encode() + file_data + f"\r\n--{boundary}--\r\n".encode()

                file_req = urllib.request.Request(
                    UPLOAD_URL + "/file",
                    data=body,
                    headers={
                        "Content-Type":   f"multipart/form-data; boundary={boundary}",
                        "Content-Length": str(len(body)),
                        "X-Api-Key":      api_key,
                        "User-Agent":     "1320CarModder/1.0",
                    }
                )
                with urllib.request.urlopen(file_req, timeout=60) as r:
                    fr = _json.loads(r.read().decode())
                if not fr.get("ok"):
                    _set(f"File error: {fr.get('error', rel_path)}", "#e94560")
                    return

            pub_note = " (public)" if meta["public"] else " (private/test)"
            _set(f"Uploaded {total} file(s){pub_note}.", "#00c87a")
            self.after(0, lambda: messagebox.showinfo(
                "Upload complete",
                f"Car {meta['car_id']} ({meta['name']}) uploaded successfully!\n"
                + ("Visible in the installer." if meta["public"]
                   else "Set as private — not shown in installer yet."),
                parent=self))
        except urllib.error.HTTPError as e:
            _set(f"HTTP {e.code}: {e.reason}", "#e94560")
        except Exception as e:
            _set(f"Upload failed: {e}", "#e94560")

    def _on_close(self):
        shutil.rmtree(self._tmp, ignore_errors=True)
        self.destroy()


if __name__ == "__main__":
    app = CarModderApp()
    app.mainloop()
