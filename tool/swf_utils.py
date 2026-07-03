"""SWF file manipulation via FFDec CLI and direct binary injection."""
import os
import struct
import zlib
import subprocess
from pathlib import Path
from PIL import Image

FFDEC_BAT: str | None = None   # set by the app at startup via set_ffdec_path()

FFDEC_DEFAULT_PATHS = [
    r"C:\Program Files (x86)\FFDec\ffdec.bat",
    r"C:\Program Files\FFDec\ffdec.bat",
]


def set_ffdec_path(path: str):
    global FFDEC_BAT
    FFDEC_BAT = path


def find_ffdec_default() -> str | None:
    """Return the first default FFDec path that exists, or None."""
    for p in FFDEC_DEFAULT_PATHS:
        if os.path.exists(p):
            return p
    return None

# SWFs below this byte size are considered procedural (no image to recolor)
MIN_IMAGE_SWF_BYTES = 1000

# Package SWF files that should NOT be recolored (tyres, undercarriage, masks are already black/grey)
SKIP_RECOLOR = {"tireF.swf", "tireR.swf", "tireBack.swf", "underCarriage.swf",
                "wheelMaskAddF.swf", "wheelMaskAddR.swf", "decalLoader.swf"}


_NO_WINDOW = 0x08000000   # CREATE_NO_WINDOW — suppresses console popup on Windows


def _run_ffdec(*args, timeout=60):
    if not FFDEC_BAT:
        raise RuntimeError("FFDec path not configured. Use File → Locate FFDec…")
    cmd = ["cmd", "/c", FFDEC_BAT] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                            creationflags=_NO_WINDOW)
    result.ok = result.returncode in (0, 255)
    return result


MIN_IMAGE_BYTES = 500  # images smaller than this are masks/effects, skip recolor


def _swf_read_bits(data: bytes, bit_pos: int, n: int, signed: bool = False):
    val = 0
    for _ in range(n):
        b = bit_pos // 8; bk = 7 - (bit_pos % 8)
        val = (val << 1) | ((data[b] >> bk) & 1)
        bit_pos += 1
    if signed and n > 0 and (val >> (n - 1)):
        val -= (1 << n)
    return val, bit_pos


def read_swf_info(swf_path: str) -> tuple[int, int, tuple[int, int, int], int, int]:
    """Parse SWF header.
    Returns (frame_w_px, frame_h_px, bg_color_rgb, origin_x_px, origin_y_px).
    origin_x/y are the RECT's xmin/ymin — the part's offset in game coordinates."""
    with open(swf_path, "rb") as f:
        raw = f.read()
    data = raw
    if raw[:3] == b"CWS":
        data = b"FWS" + raw[3:8] + zlib.decompress(raw[8:])
    # RECT bit-stream starts at byte 8
    bit_pos = 8 * 8
    nbits, bit_pos = _swf_read_bits(data, bit_pos, 5)
    xmin, bit_pos = _swf_read_bits(data, bit_pos, nbits, signed=True)
    xmax, bit_pos = _swf_read_bits(data, bit_pos, nbits, signed=True)
    ymin, bit_pos = _swf_read_bits(data, bit_pos, nbits, signed=True)
    ymax, bit_pos = _swf_read_bits(data, bit_pos, nbits, signed=True)
    w_px    = max(0, xmax - xmin) // 20
    h_px    = max(0, ymax - ymin) // 20
    orig_x  = xmin // 20
    orig_y  = ymin // 20
    # Scan tags for SetBackgroundColor (tag 9)
    rbytes = (5 + 4 * nbits + 7) // 8
    pos = 8 + rbytes + 4
    bg: tuple[int, int, int] = (0, 0, 0)
    while pos + 2 <= len(data):
        hdr = struct.unpack_from("<H", data, pos)[0]; pos += 2
        tt = hdr >> 6; tl = hdr & 0x3F
        if tl == 0x3F:
            tl = struct.unpack_from("<i", data, pos)[0]; pos += 4
        if tt == 9 and tl >= 3:
            bg = (data[pos], data[pos + 1], data[pos + 2])
            break
        if tt == 0:
            break
        pos += tl
    return w_px, h_px, bg, orig_x, orig_y


def export_swf_frame(swf_path: str, out_dir: str) -> "str | None":
    """Render the first frame of a SWF via FFDec at its native stage dimensions.
    Returns path to the exported PNG, or None on failure."""
    os.makedirs(out_dir, exist_ok=True)
    _run_ffdec("-export", "frame", out_dir, swf_path, timeout=60)
    for p in sorted(Path(out_dir).glob("**/*.png")):
        if p.stat().st_size > 100:
            return str(p)
    return None


def export_image(swf_path: str, out_dir: str) -> str | None:
    """Export the largest embedded image from a SWF. Returns file path or None."""
    images = export_all_images(swf_path, out_dir)
    if not images:
        return None
    return max(images.values(), key=lambda p: os.path.getsize(p))


def export_all_images(swf_path: str, out_dir: str) -> dict[int, str]:
    """Export all embedded images from a SWF.
    Returns {char_id: file_path} for images above MIN_IMAGE_BYTES."""
    os.makedirs(out_dir, exist_ok=True)
    _run_ffdec("-export", "image", out_dir, swf_path, timeout=30)
    result = {}
    for p in Path(out_dir).glob("**/*"):
        if not p.is_file():
            continue
        if p.stat().st_size < MIN_IMAGE_BYTES:
            continue
        # FFDec names files as {char_id}.png or {char_id}.jpg
        stem = p.stem
        if stem.isdigit():
            result[int(stem)] = str(p)
    return result


def replace_image_in_swf(src_swf: str, new_image: str, out_swf: str,
                          char_id: int = 1) -> bool:
    """Replace a single character in src_swf with new_image, writing to out_swf."""
    result = _run_ffdec("-replace", src_swf, out_swf, str(char_id), new_image, timeout=45)
    return result.ok and os.path.exists(out_swf)


def replace_all_images_in_swf(src_swf: str, replacements: dict[int, str],
                                out_swf: str) -> bool:
    """Replace multiple image characters in a SWF (chained).
    replacements: {char_id: new_image_path}"""
    import shutil, tempfile
    if not replacements:
        shutil.copy2(src_swf, out_swf)
        return True

    items = list(replacements.items())
    tmp_files = []
    current_src = src_swf

    try:
        for i, (char_id, new_img) in enumerate(items):
            is_last = (i == len(items) - 1)
            if is_last:
                dest = out_swf
            else:
                tmp = tempfile.NamedTemporaryFile(suffix=".swf", delete=False)
                tmp.close()
                dest = tmp.name
                tmp_files.append(dest)

            result = _run_ffdec("-replace", current_src, dest, str(char_id), new_img,
                                 timeout=45)
            if not result.ok or not os.path.exists(dest):
                return False
            current_src = dest
    finally:
        for f in tmp_files:
            if f != out_swf:
                try:
                    os.unlink(f)
                except OSError:
                    pass

    return os.path.exists(out_swf)


def export_badge_images(swf_path: str, out_dir: str) -> dict[int, dict]:
    """Export badge images from badges.swf.
    Returns {badge_id: {'small': (char_id, path), 'large': (char_id, path)}}"""
    os.makedirs(out_dir, exist_ok=True)
    _run_ffdec("-export", "image", out_dir, swf_path, timeout=120)
    result = {}
    for p in Path(out_dir).glob("*.png"):
        # FFDec names: "{charId}_{linkageName}.png" e.g. "1002_badge160.png" / "100_badge572_l.png"
        stem = p.stem
        under = stem.find("_")
        if under < 0:
            continue
        char_id_str, name = stem[:under], stem[under + 1:]
        if not char_id_str.isdigit() or not name.startswith("badge"):
            continue
        badge_part = name[5:]  # strip "badge"
        is_large = badge_part.endswith("_l")
        badge_id_str = badge_part[:-2] if is_large else badge_part
        if not badge_id_str.isdigit():
            continue
        char_id = int(char_id_str)
        badge_id = int(badge_id_str)
        entry = result.setdefault(badge_id, {})
        entry["large" if is_large else "small"] = (char_id, str(p))
    return result


# ── SWF binary helpers ────────────────────────────────────────────────────────

def _swf_load(path: str) -> bytearray:
    """Read SWF, decompress if needed, return raw uncompressed bytes."""
    with open(path, 'rb') as f:
        data = bytearray(f.read())
    if data[:3] == b'CWS':
        body = zlib.decompress(data[8:])
        data = bytearray(data[:8]) + bytearray(body)
        data[0:3] = b'FWS'
    elif data[:3] not in (b'FWS', b'ZWS'):
        raise ValueError(f"Unknown SWF signature: {data[:3]}")
    return data


def _swf_tags_start(data: bytearray) -> int:
    nbits = (data[8] >> 3) & 0x1F
    rect_bits = 5 + 4 * nbits
    return 8 + (rect_bits + 7) // 8 + 4  # +4 = FrameRate + FrameCount


def _swf_iter_tags(data: bytearray, tags_start: int):
    """Yield (tag_type, data_start, tag_len, pos) for each tag."""
    pos = tags_start
    while pos + 2 <= len(data):
        rh = struct.unpack_from('<H', data, pos)[0]
        tag_type = rh >> 6
        raw_len  = rh & 0x3F
        if raw_len == 0x3F:
            tag_len = struct.unpack_from('<I', data, pos + 2)[0]
            ds = pos + 6
        else:
            tag_len = raw_len
            ds = pos + 2
        yield tag_type, ds, tag_len, pos
        if tag_type == 0:
            break
        pos = ds + tag_len


def _swf_end_pos(data: bytearray, tags_start: int) -> int:
    for tag_type, ds, tag_len, pos in _swf_iter_tags(data, tags_start):
        if tag_type == 0:
            return pos
    return len(data)


def _swf_max_char_id(data: bytearray, tags_start: int) -> int:
    DEFINE_TAGS = {2, 6, 20, 21, 22, 32, 34, 35, 36, 37, 39, 46, 83}
    max_id = 0
    for tag_type, ds, tag_len, _ in _swf_iter_tags(data, tags_start):
        if tag_type in DEFINE_TAGS and tag_len >= 2:
            max_id = max(max_id, struct.unpack_from('<H', data, ds)[0])
        if tag_type == 56 and tag_len >= 2:  # ExportAssets
            count = struct.unpack_from('<H', data, ds)[0]
            ep = ds + 2
            for _ in range(count):
                if ep + 2 > ds + tag_len:
                    break
                max_id = max(max_id, struct.unpack_from('<H', data, ep)[0])
                ep += 2
                while ep < ds + tag_len and data[ep] != 0:
                    ep += 1
                ep += 1
    return max_id


def _swf_existing_badge_ids(data: bytearray, tags_start: int) -> set[int]:
    """Return badge IDs that already exist as ExportAssets in the SWF."""
    ids = set()
    for tag_type, ds, tag_len, _ in _swf_iter_tags(data, tags_start):
        if tag_type != 56 or tag_len < 2:
            continue
        count = struct.unpack_from('<H', data, ds)[0]
        ep = ds + 2
        for _ in range(count):
            if ep + 2 > ds + tag_len:
                break
            ep += 2  # skip char id
            name_start = ep
            while ep < ds + tag_len and data[ep] != 0:
                ep += 1
            name = data[name_start:ep].decode('ascii', errors='ignore')
            ep += 1
            import re
            m = re.fullmatch(r'badge(\d+)(_l)?', name)
            if m:
                ids.add(int(m.group(1)))
    return ids


def _swf_get_count(data: bytearray, tags_start: int) -> int:
    """Find the loop count constant in DoAction (var count = X)."""
    for tag_type, ds, tag_len, _ in _swf_iter_tags(data, tags_start):
        if tag_type != 12:  # DoAction
            continue
        for i in range(ds, ds + tag_len - 6):
            if data[i] == 0x96 and data[i + 3] == 0x07:  # Push int32
                val = struct.unpack_from('<I', data, i + 4)[0]
                if 100 <= val <= 9999:
                    return val
    return 622


def _swf_patch_count(data: bytearray, tags_start: int, old_val: int, new_val: int) -> bytearray:
    """Replace the loop count constant in DoAction."""
    data = bytearray(data)
    for tag_type, ds, tag_len, _ in _swf_iter_tags(data, tags_start):
        if tag_type != 12:
            continue
        for i in range(ds, ds + tag_len - 6):
            if data[i] == 0x96 and data[i + 3] == 0x07:
                val = struct.unpack_from('<I', data, i + 4)[0]
                if val == old_val:
                    struct.pack_into('<I', data, i + 4, new_val)
                    return data
    return data


# ── SWF bit-stream writer ──────────────────────────────────────────────────────

class _BitWriter:
    def __init__(self):
        self._bits: list[int] = []

    def write(self, val: int, n: int):
        if n <= 0:
            return
        if val < 0:
            val += (1 << n)
        for i in range(n - 1, -1, -1):
            self._bits.append((val >> i) & 1)

    @staticmethod
    def nbits_signed(*vals: int) -> int:
        if not vals or all(v == 0 for v in vals):
            return 1
        return max(abs(v).bit_length() + 1 for v in vals)

    def to_bytes(self) -> bytes:
        bits = self._bits[:]
        while len(bits) % 8:
            bits.append(0)
        out = bytearray()
        for i in range(0, len(bits), 8):
            b = 0
            for j in range(8):
                b = (b << 1) | bits[i + j]
            out.append(b)
        return bytes(out)


def _encode_rect_twips(xmin: int, xmax: int, ymin: int, ymax: int) -> bytes:
    bw = _BitWriter()
    nb = _BitWriter.nbits_signed(xmin, xmax, ymin, ymax)
    bw.write(nb, 5)
    bw.write(xmin, nb); bw.write(xmax, nb)
    bw.write(ymin, nb); bw.write(ymax, nb)
    return bw.to_bytes()


def _encode_matrix_identity() -> bytes:
    bw = _BitWriter()
    bw.write(0, 1)  # HasScale=0
    bw.write(0, 1)  # HasRotate=0
    bw.write(0, 1)  # HasTranslate=0
    return bw.to_bytes()


def _encode_matrix_scale20() -> bytes:
    """Scale matrix: 1 px = 20 twips, for bitmap fill coordinate mapping."""
    sx = sy = 20 * 65536   # 16.16 fixed-point
    bw = _BitWriter()
    nb = _BitWriter.nbits_signed(sx, sy)
    bw.write(1, 1); bw.write(nb, 5)
    bw.write(sx, nb); bw.write(sy, nb)
    bw.write(0, 1)  # HasRotate=0
    bw.write(0, 1)  # HasTranslate=0
    return bw.to_bytes()


def _tag_define_shape4_bitmap(shape_id: int, bitmap_id: int,
                               w_px: int, h_px: int) -> bytes:
    """DefineShape4 (tag 83): solid rectangle filled with bitmap_id."""
    W, H = w_px * 20, h_px * 20   # twips

    bounds = _encode_rect_twips(0, W, 0, H)

    # FillStyleArray: 1 entry — clipped non-smoothed bitmap fill (0x40)
    fill = struct.pack('<BH', 0x40, bitmap_id) + _encode_matrix_scale20()
    fill_arr = struct.pack('<B', 1) + fill
    line_arr = struct.pack('<B', 0)              # no line styles
    num_bits = struct.pack('<B', (1 << 4) | 0)  # NumFillBits=1, NumLineBits=0

    bw = _BitWriter()
    # StyleChangeRecord: StateMoveTo=1, StateFillStyle0=1
    bw.write(0, 1); bw.write(0, 1); bw.write(0, 1)
    bw.write(0, 1); bw.write(1, 1); bw.write(1, 1)  # StateFillStyle0, StateMoveTo
    bw.write(1, 5); bw.write(0, 1); bw.write(0, 1)  # MoveBits=1, x=0, y=0
    bw.write(1, 1)                                    # FillStyle0 index=1

    # 4 straight edges forming the rectangle
    for dx, dy in [(W, 0), (0, H), (-W, 0), (0, -H)]:
        nb = max(_BitWriter.nbits_signed(dx if dx else 1, dy if dy else 1), 2)
        bw.write(1, 1); bw.write(1, 1)    # TypeFlag=1, StraightFlag=1
        bw.write(nb - 2, 4)               # NumBits (stored as n-2)
        if dy == 0:
            bw.write(0, 1); bw.write(0, 1)  # GeneralLine=0, Vert=0
            bw.write(dx, nb)
        else:
            bw.write(0, 1); bw.write(1, 1)  # GeneralLine=0, Vert=1
            bw.write(dy, nb)

    bw.write(0, 6)   # EndShapeRecord

    payload = (struct.pack('<H', shape_id) +
               bounds + bounds + b'\x00' +
               fill_arr + line_arr + num_bits +
               bw.to_bytes())
    return _make_tag(83, payload)


def _tag_place_object2(char_id: int, depth: int = 1) -> bytes:
    payload = (struct.pack('<BHH', 0x06, depth, char_id) +
               _encode_matrix_identity())
    return _make_tag(26, payload)


def build_part_swf(img: Image.Image, output_path: str,
                   stage_w: int | None = None, stage_h: int | None = None,
                   offset_x: int = 0, offset_y: int = 0) -> bool:
    """
    Build a minimal SWF from img and write to output_path.
    stage_w/h default to image size. offset_x/y place the image on the stage.
    Returns True on success.
    """
    try:
        img = img.convert("RGBA")
        iw, ih = img.size
        sw = stage_w or iw
        sh = stage_h or ih

        if sw != iw or sh != ih or offset_x != 0 or offset_y != 0:
            canvas = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
            canvas.paste(img, (offset_x, offset_y), img)
            img = canvas

        tags = (
            _make_tag(69, struct.pack('<I', 0)) +    # FileAttributes
            _make_tag(9,  b'\xff\xff\xff') +          # SetBackgroundColor white
            _tag_define_bits_lossless2(1, img) +
            _tag_define_shape4_bitmap(2, 1, sw, sh) +
            _tag_place_object2(2, depth=1) +
            _make_tag(1, b'') +                       # ShowFrame
            _make_tag(0, b'')                         # End
        )
        rect       = _encode_rect_twips(0, sw * 20, 0, sh * 20)
        frame_info = struct.pack('<HH', 24 * 256, 1)  # 24 fps, 1 frame
        header     = b'FWS' + bytes([10]) + struct.pack('<I', 8 + len(rect) + len(frame_info) + len(tags))
        with open(output_path, 'wb') as f:
            f.write(header + rect + frame_info + tags)
        return True
    except Exception as e:
        print(f"build_part_swf error: {e}")
        import traceback; traceback.print_exc()
        return False


def _make_tag(tag_type: int, payload: bytes) -> bytes:
    if len(payload) < 63:
        return struct.pack('<H', (tag_type << 6) | len(payload)) + payload
    return struct.pack('<HI', (tag_type << 6) | 0x3F, len(payload)) + payload


def _tag_define_bits_lossless2(char_id: int, img: Image.Image) -> bytes:
    """Build DefineBitsLossless2 (tag 36) with pre-multiplied ARGB data."""
    img = img.convert("RGBA")
    W, H = img.size
    buf = bytearray(W * H * 4)
    for i, (r, g, b, a) in enumerate(img.getdata()):
        fa = a / 255.0
        buf[i * 4]     = a
        buf[i * 4 + 1] = min(255, int(r * fa + 0.5))
        buf[i * 4 + 2] = min(255, int(g * fa + 0.5))
        buf[i * 4 + 3] = min(255, int(b * fa + 0.5))
    payload = struct.pack('<HBHH', char_id, 5, W, H) + zlib.compress(bytes(buf), 6)
    return _make_tag(36, payload)


def _tag_export_assets(exports: list[tuple[int, str]]) -> bytes:
    payload = struct.pack('<H', len(exports))
    for cid, name in exports:
        payload += struct.pack('<H', cid) + name.encode('ascii') + b'\x00'
    return _make_tag(56, payload)


def add_badges_to_swf(swf_path: str, new_badges: list[dict], out_path: str) -> bool:
    """
    Inject new badges into badges.swf without touching existing ones.
    new_badges: [{'badge_id': int, 'small': PIL.Image, 'large': PIL.Image|None}]
    If 'large' is None, the small image is used for both sizes.
    Returns True on success.
    """
    try:
        data = _swf_load(swf_path)
        ts   = _swf_tags_start(data)

        max_cid     = _swf_max_char_id(data, ts)
        old_count   = _swf_get_count(data, ts)
        max_new_bid = max(nb['badge_id'] for nb in new_badges)

        # Patch count if any new ID exceeds current loop bound
        if max_new_bid > old_count:
            data = _swf_patch_count(data, ts, old_count, max_new_bid)
            ts   = _swf_tags_start(data)

        end_pos  = _swf_end_pos(data, ts)
        next_cid = max_cid + 1
        new_tags = bytearray()

        for nb in new_badges:
            bid   = nb['badge_id']
            small = nb['small']
            large = nb.get('large') or small

            scid = next_cid;     next_cid += 1
            lcid = next_cid;     next_cid += 1

            new_tags += _tag_define_bits_lossless2(scid, small)
            new_tags += _tag_export_assets([(scid, f"badge{bid}")])
            new_tags += _tag_define_bits_lossless2(lcid, large)
            new_tags += _tag_export_assets([(lcid, f"badge{bid}_l")])

        result = bytearray(data[:end_pos]) + new_tags + bytearray(data[end_pos:])
        struct.pack_into('<I', result, 4, len(result))

        with open(out_path, 'wb') as f:
            f.write(result)
        return True
    except Exception as e:
        print(f"add_badges_to_swf error: {e}")
        import traceback; traceback.print_exc()
        return False


def get_swf_badge_gap_ids(swf_path: str) -> list[int]:
    """Return badge IDs in [1, count] that are not yet defined in the SWF."""
    data = _swf_load(swf_path)
    ts   = _swf_tags_start(data)
    count   = _swf_get_count(data, ts)
    existing = _swf_existing_badge_ids(data, ts)
    return [i for i in range(1, count + 1) if i not in existing]


def swf_rect_origin(path: str) -> tuple:
    """Return (xmin_px, ymin_px, width_px, height_px) of a SWF's stage bounding box."""
    try:
        with open(path, 'rb') as f:
            data = f.read(32)
        nbits = (data[8] >> 3) & 0x1F
        n_bytes = (5 + 4 * nbits + 7) // 8
        bits = int.from_bytes(data[8:8 + n_bytes], 'big')
        total = n_bytes * 8
        shift = total - 5

        def nxt():
            nonlocal shift
            mask = (1 << nbits) - 1
            v = (bits >> (shift - nbits)) & mask
            if v >= (1 << (nbits - 1)):
                v -= (1 << nbits)
            shift -= nbits
            return v / 20.0

        xmin = nxt(); xmax = nxt(); ymin = nxt(); ymax = nxt()
        return xmin, ymin, xmax - xmin, ymax - ymin
    except Exception:
        return 0.0, 0.0, 0.0, 0.0


def parse_tire_swf(path: str) -> dict:
    """Read tx, ty, scx, scy from a tire position SWF (tireF.swf / tireR.swf).
    Returns dict with present keys; missing keys default to 100 for scx/scy, 0 for tx/ty."""
    try:
        with open(path, 'rb') as f:
            data = bytearray(f.read())
    except OSError:
        return {}

    assignments = {}

    def _parse_doaction(bp, be):
        last_push = []
        while bp < be:
            op = data[bp]
            if op == 0x96:  # Push
                sz = struct.unpack_from('<H', data, bp + 1)[0]
                items = []
                ip = bp + 3
                ie = ip + sz
                while ip < ie:
                    t = data[ip]; ip += 1
                    if t == 0x00:   # string
                        end = data.index(0, ip)
                        items.append(data[ip:end].decode('ascii', errors='ignore'))
                        ip = end + 1
                    elif t == 0x07: # int32
                        items.append(struct.unpack_from('<i', data, ip)[0])
                        ip += 4
                    elif t == 0x06: # double (Flash: [hi4LE][lo4LE])
                        hi = struct.unpack_from('<I', data, ip)[0]
                        lo = struct.unpack_from('<I', data, ip + 4)[0]
                        items.append(struct.unpack('>d', struct.pack('>II', hi, lo))[0])
                        ip += 8
                    elif t == 0x01: # float32
                        items.append(struct.unpack_from('<f', data, ip)[0])
                        ip += 4
                    else:
                        break
                last_push = items
                bp += 3 + sz
            elif op == 0x1d:  # SetVariable: val = stack top, name = below
                if len(last_push) >= 2:
                    val, name = last_push[-1], last_push[-2]
                    if isinstance(name, str) and name:
                        assignments[name] = val
                last_push = []
                bp += 1
            elif op == 0:
                break
            else:
                bp += 1

    def _walk(start, end):
        p = start
        while p < end:
            if p + 2 > end:
                break
            rh = struct.unpack_from('<H', data, p)[0]
            tag_type = rh >> 6
            raw_len  = rh & 0x3F
            if raw_len == 0x3F:
                tlen = struct.unpack_from('<I', data, p + 2)[0]
                ds   = p + 6
            else:
                tlen = raw_len
                ds   = p + 2
            if tag_type == 39:  # DefineSprite — recurse into inner tags
                _walk(ds + 4, ds + tlen)
            elif tag_type == 12:  # DoAction
                _parse_doaction(ds, ds + tlen)
            if tag_type == 0:
                break
            p = ds + tlen

    nbits = (data[8] >> 3) & 0x1F
    ts = 8 + (5 + 4 * nbits + 7) // 8 + 4
    _walk(ts, len(data))
    return assignments


def patch_tire_swf(src_path: str, dest_path: str, overrides: dict) -> bool:
    """Write a modified tire SWF with updated tx/ty/scx/scy values.
    overrides: {var_name: new_value}  — only specified variables are changed.
    Supports int32 (type 0x07) and double (type 0x06) in-place patching."""
    try:
        with open(src_path, 'rb') as f:
            data = bytearray(f.read())
    except OSError:
        return False

    patched = {}  # track which vars were patched

    def _patch_doaction(bp, be):
        last_push_items = []   # list of (value, type_byte, offset_in_data)
        while bp < be:
            op = data[bp]
            if op == 0x96:
                sz = struct.unpack_from('<H', data, bp + 1)[0]
                items = []
                ip = bp + 3
                ie = ip + sz
                while ip < ie:
                    t = data[ip]; ip += 1
                    if t == 0x00:
                        end = data.index(0, ip)
                        items.append((data[ip:end].decode('ascii', 'ignore'), t, None))
                        ip = end + 1
                    elif t == 0x07:
                        v = struct.unpack_from('<i', data, ip)[0]
                        items.append((v, t, ip))
                        ip += 4
                    elif t == 0x06:
                        hi = struct.unpack_from('<I', data, ip)[0]
                        lo = struct.unpack_from('<I', data, ip + 4)[0]
                        v = struct.unpack('>d', struct.pack('>II', hi, lo))[0]
                        items.append((v, t, ip))
                        ip += 8
                    elif t == 0x01:
                        v = struct.unpack_from('<f', data, ip)[0]
                        items.append((v, t, ip))
                        ip += 4
                    else:
                        break
                last_push_items = items
                bp += 3 + sz
            elif op == 0x1d:  # SetVariable
                if len(last_push_items) >= 2:
                    val_item  = last_push_items[-1]   # (value, type, offset)
                    name_item = last_push_items[-2]   # (name_str, 0x00, None)
                    name = name_item[0] if isinstance(name_item[0], str) else None
                    if name and name in overrides and name not in patched:
                        new_val = overrides[name]
                        vtype   = val_item[1]
                        voff    = val_item[2]
                        if voff is not None:
                            if vtype == 0x07:   # int32
                                struct.pack_into('<i', data, voff, int(round(new_val)))
                                patched[name] = new_val
                            elif vtype == 0x06: # double (Flash word-swap)
                                fv = float(new_val)
                                raw = struct.pack('>d', fv)
                                # Flash stores [hi4][lo4] each in LE → byte order reversal
                                hi = struct.unpack('>I', raw[:4])[0]
                                lo = struct.unpack('>I', raw[4:])[0]
                                struct.pack_into('<I', data, voff,     hi)
                                struct.pack_into('<I', data, voff + 4, lo)
                                patched[name] = new_val
                last_push_items = []
                bp += 1
            elif op == 0:
                break
            else:
                bp += 1

    def _walk(start, end):
        p = start
        while p < end:
            if p + 2 > end:
                break
            rh = struct.unpack_from('<H', data, p)[0]
            tag_type = rh >> 6
            raw_len  = rh & 0x3F
            if raw_len == 0x3F:
                tlen = struct.unpack_from('<I', data, p + 2)[0]
                ds   = p + 6
            else:
                tlen = raw_len
                ds   = p + 2
            if tag_type == 39:
                _walk(ds + 4, ds + tlen)
            elif tag_type == 12:
                _patch_doaction(ds, ds + tlen)
            if tag_type == 0:
                break
            p = ds + tlen

    nbits = (data[8] >> 3) & 0x1F
    ts = 8 + (5 + 4 * nbits + 7) // 8 + 4
    _walk(ts, len(data))

    try:
        with open(dest_path, 'wb') as f:
            f.write(data)
        return True
    except OSError:
        return False


def get_package_info(packages_dir: str) -> dict[int, dict]:
    """Scan packages dir and return {car_id: {'f': path, 'b': path, 'both': bool}}"""
    cars = {}
    for entry in Path(packages_dir).iterdir():
        if not entry.is_dir():
            continue
        name = entry.name
        if name.endswith("f") and name[:-1].isdigit():
            car_id = int(name[:-1])
            cars.setdefault(car_id, {})["f"] = str(entry)
        elif name.endswith("b") and name[:-1].isdigit():
            car_id = int(name[:-1])
            cars.setdefault(car_id, {})["b"] = str(entry)
    return cars


def should_recolor(swf_path: str) -> bool:
    """Return True if this SWF contains an image worth recoloring."""
    fname = os.path.basename(swf_path)
    if fname in SKIP_RECOLOR:
        return False
    return os.path.getsize(swf_path) >= MIN_IMAGE_SWF_BYTES


def list_visual_swfs(package_dir: str) -> list[str]:
    """Return SWF paths in a package dir that contain images to recolor."""
    result = []
    for swf in Path(package_dir).glob("*.swf"):
        if should_recolor(str(swf)):
            result.append(str(swf))
    return result
