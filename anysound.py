"""AnySound - arraste um vídeo ou áudio: converte para áudio e/ou equaliza o volume."""
import json
import math
import os
import queue
import random
import re
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, ttk

import imageio_ffmpeg

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DnDBase = TkinterDnD.DnDWrapper
except ImportError:
    DND_FILES, TkinterDnD, DnDBase = None, None, object

APP = "AnySound"
KEEP = "Manter formato"
FORMATS = {
    "MP3": ("mp3", ["-c:a", "libmp3lame"]),
    "WAV": ("wav", ["-c:a", "pcm_s16le"]),
    "FLAC": ("flac", ["-c:a", "flac"]),
    "OGG": ("ogg", ["-c:a", "libvorbis"]),
    "M4A": ("m4a", ["-c:a", "aac"]),
    "OPUS": ("opus", ["-c:a", "libopus"]),
}
BITRATES = ["320k", "256k", "192k", "128k", "96k"]
LOSSLESS = {"wav", "flac"}
VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv", ".m4v", ".mpg",
              ".mpeg", ".3gp", ".ts", ".m2ts", ".mts", ".m2t", ".tsv", ".trp"}
AUDIO_EXTS = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".opus", ".aac", ".wma"}
# Codec de áudio usado ao manter o formato original (vídeo é copiado sem recodificar).
KEEP_CODEC = {
    ".webm": "libopus", ".opus": "libopus", ".ogg": "libvorbis", ".avi": "libmp3lame",
    ".mp3": "libmp3lame", ".wav": "pcm_s16le", ".flac": "flac", ".wma": "wmav2",
    ".wmv": "wmav2", ".mpg": "mp2", ".mpeg": "mp2",
}
# Equalização de vozes, suave: aproxima locutores/distâncias sem achatar a dinâmica.
VOICE_LEVELER = ",".join([
    "highpass=f=70",
    "dynaudnorm=f=250:g=15:p=0.95:m=10",
    "acompressor=threshold=-16dB:ratio=2:attack=20:release=300:knee=6",
    "loudnorm=I=-16:TP=-1.5:LRA=11",
    "alimiter=limit=0.84:attack=5:release=50:level=disabled",
    "aresample=48000",
])
NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

ORANGE, ORANGE_DARK, CREAM, INK = "#D97757", "#C15F3C", "#FAF9F5", "#3D2A20"
W, H = 560, 330
CONFIG_PATH = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~/.config"),
                           APP, "config.json")
DEFAULTS = {"format": KEEP, "level": True, "bitrate": "192k", "outdir": "", "open_folder": False}


def load_config():
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return {**DEFAULTS, **json.load(f)}
    except (OSError, ValueError):
        return dict(DEFAULTS)


def save_config(cfg):
    try:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except OSError:
        pass


def parse_time(text):
    h, m, s = text.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def unique_path(path):
    base, ext = os.path.splitext(path)
    n = 1
    while os.path.exists(path):
        path = f"{base} ({n}){ext}"
        n += 1
    return path


def build_command(src, cfg):
    """Retorna (comando ffmpeg, arquivo de saída) ou levanta ValueError."""
    name, ext = os.path.splitext(os.path.basename(src))
    ext = ext.lower()
    out_dir = cfg["outdir"] or os.path.dirname(src)
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-hide_banner",
           "-fflags", "+genpts+discardcorrupt", "-i", src]
    if cfg["format"] == KEEP:
        if not cfg["level"]:
            raise ValueError("Nada a fazer: escolha um formato ou ative Equalizar volume")
        codec = KEEP_CODEC.get(ext, "aac")
        dest = unique_path(os.path.join(out_dir, f"{name} (normalizado){ext}"))
        cmd += ["-map", "0", "-c", "copy", "-c:a", codec]
        lossless = codec in ("pcm_s16le", "flac")
    else:
        out_ext, codec_args = FORMATS[cfg["format"]]
        dest = unique_path(os.path.join(out_dir, f"{name}.{out_ext}"))
        cmd += ["-map", "0:a:0", "-vn", "-sn", "-dn", *codec_args]
        lossless = out_ext in LOSSLESS
    if cfg["level"]:
        cmd += ["-af", VOICE_LEVELER]
    if not lossless:
        cmd += ["-b:a", cfg["bitrate"]]
    return cmd + [dest], dest


def run_ffmpeg(cmd, dest, on_progress):
    proc = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL,
                            stdin=subprocess.DEVNULL, universal_newlines=True,
                            encoding="utf-8", errors="replace", creationflags=NO_WINDOW)
    duration, tail = None, []
    for line in iter(proc.stderr.readline, ""):
        tail = (tail + [line.strip()])[-5:]
        if duration is None:
            m = re.search(r"Duration: (\d+:\d+:[\d.]+)", line)
            if m:
                duration = parse_time(m.group(1)) or None
        m = re.search(r"time=(\d+:\d+:[\d.]+)", line)
        if m and duration:
            on_progress(min(parse_time(m.group(1)) / duration, 1.0))
    if proc.wait() != 0:
        if os.path.exists(dest):
            os.remove(dest)
        raise RuntimeError(tail[-1] if tail else "falha no ffmpeg")


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


class App(tk.Tk, DnDBase):
    def __init__(self):
        super().__init__()
        try:
            TkinterDnD._require(self)
            self.dnd = True
        except Exception:  # tkdnd ausente ou incompatível com esta versão do Tk
            self.dnd = False
        self.title(APP)
        self.geometry(f"{W}x{H}")
        self.resizable(False, False)
        self.configure(bg=ORANGE)
        icon = os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(__file__)), "anysound.ico")
        if sys.platform == "win32" and os.path.exists(icon):
            self.iconbitmap(icon)

        self.cfg = load_config()
        self.jobs = queue.Queue()
        self.state = "idle"          # idle -> morph_in -> working -> done -> morph_out -> idle
        self.state_t = 0.0
        self.progress = 0.0
        self.message = "Arraste um vídeo ou áudio aqui"
        self.phase = 0.0
        self.bars = [random.uniform(0.25, 1.0) for _ in range(36)]

        self._build_toolbar()
        self.canvas = tk.Canvas(self, width=W, height=H - 44, bg=ORANGE, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        if self.dnd:
            for widget in (self, self.canvas):
                widget.drop_target_register(DND_FILES)
                widget.dnd_bind("<<Drop>>", self.on_drop)
        else:
            self.message = "Clique aqui para escolher um vídeo"
        self.canvas.bind("<Button-1>", self.on_click)

        threading.Thread(target=self.worker, daemon=True).start()
        self.tick()

    # ---------- interface ----------
    def _build_toolbar(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("A.TCombobox", fieldbackground=CREAM, background=CREAM,
                        foreground=INK, arrowcolor=INK, bordercolor=ORANGE_DARK)
        style.map("A.TCombobox", fieldbackground=[("readonly", CREAM)],
                  foreground=[("readonly", INK)])
        bar = tk.Frame(self, bg=ORANGE_DARK, height=44)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        self.fmt = tk.StringVar(value=self.cfg["format"])
        box = ttk.Combobox(bar, textvariable=self.fmt, values=[KEEP, *FORMATS],
                           state="readonly", width=15, style="A.TCombobox")
        box.pack(side="left", padx=(12, 8), pady=9)
        box.bind("<<ComboboxSelected>>", lambda e: self.store())

        self.level = tk.BooleanVar(value=self.cfg["level"])
        tk.Checkbutton(bar, text="Equalizar volume", variable=self.level, command=self.store,
                       bg=ORANGE_DARK, fg=CREAM, selectcolor=ORANGE, activebackground=ORANGE_DARK,
                       activeforeground=CREAM, highlightthickness=0, bd=0,
                       font=("Segoe UI", 10)).pack(side="left")

        more = tk.Label(bar, text="•••", bg=ORANGE_DARK, fg=CREAM, cursor="hand2",
                        font=("Segoe UI", 12, "bold"))
        more.pack(side="right", padx=14)
        more.bind("<Button-1>", lambda e: self.open_settings())

    def store(self):
        self.cfg["format"] = self.fmt.get()
        self.cfg["level"] = self.level.get()
        save_config(self.cfg)

    def open_settings(self):
        win = tk.Toplevel(self, bg=CREAM, padx=16, pady=12)
        win.title("Configurações")
        win.resizable(False, False)
        win.transient(self)
        outdir = tk.StringVar(value=self.cfg["outdir"])
        bitrate = tk.StringVar(value=self.cfg["bitrate"])
        open_folder = tk.BooleanVar(value=self.cfg["open_folder"])

        lbl = {"bg": CREAM, "fg": INK, "anchor": "w"}
        tk.Label(win, text="Salvar em (vazio = mesma pasta do arquivo):", **lbl).grid(
            row=0, column=0, columnspan=2, sticky="w")
        ttk.Entry(win, textvariable=outdir, width=42).grid(row=1, column=0, sticky="we")
        ttk.Button(win, text="...", width=3, command=lambda: outdir.set(
            filedialog.askdirectory(parent=win) or outdir.get())).grid(row=1, column=1, padx=4)
        tk.Label(win, text="Qualidade (MP3, OGG, M4A, OPUS e áudio de vídeos):", **lbl).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(10, 0))
        ttk.Combobox(win, textvariable=bitrate, values=BITRATES, state="readonly",
                     width=8).grid(row=3, column=0, sticky="w")
        tk.Checkbutton(win, text="Abrir a pasta ao terminar", variable=open_folder, bg=CREAM,
                       fg=INK, activebackground=CREAM, highlightthickness=0).grid(
            row=4, column=0, sticky="w", pady=(10, 0))

        def close():
            self.cfg.update(outdir=outdir.get().strip(), bitrate=bitrate.get(),
                            open_folder=open_folder.get())
            save_config(self.cfg)
            win.destroy()

        ttk.Button(win, text="OK", command=close).grid(row=5, column=1, pady=(12, 0))
        win.protocol("WM_DELETE_WINDOW", close)
        win.grab_set()

    # ---------- arquivos ----------
    def on_click(self, _event):
        if self.state == "idle" and not self.dnd:
            exts = " ".join("*" + e for e in sorted(VIDEO_EXTS | AUDIO_EXTS))
            self.enqueue(filedialog.askopenfilenames(filetypes=[("Vídeos e áudios", exts)]))

    def on_drop(self, event):
        self.enqueue(self.tk.splitlist(event.data))

    def enqueue(self, paths):
        found = []
        for p in paths:
            if os.path.isdir(p):
                for root, _, names in os.walk(p):
                    found += [os.path.join(root, n) for n in sorted(names)]
            else:
                found.append(p)
        found = [os.path.normpath(f) for f in found
                 if os.path.splitext(f)[1].lower() in VIDEO_EXTS | AUDIO_EXTS]
        if not found:
            self.flash("Arquivo não suportado")
            return
        snapshot = dict(self.cfg, format=self.fmt.get(), level=self.level.get())
        for f in found:
            self.jobs.put((f, snapshot))

    def flash(self, text):
        self.after(0, lambda: setattr(self, "message", text))

    def worker(self):
        while True:
            src, cfg = self.jobs.get()
            self.progress = 0.0
            if self.state in ("idle", "morph_out"):
                self.set_state("morph_in")
            remaining = self.jobs.qsize()
            self.message = os.path.basename(src) + (f"  (+{remaining} na fila)" if remaining else "")
            try:
                cmd, dest = build_command(src, cfg)
                run_ffmpeg(cmd, dest, lambda p: setattr(self, "progress", p))
                self.progress = 1.0
                result = "Pronto!  " + os.path.basename(dest)
                if cfg["open_folder"] and self.jobs.empty() and sys.platform == "win32":
                    subprocess.Popen(["explorer", "/select,", dest])
            except Exception as e:
                result = f"Erro: {e}"[:90]
            if self.jobs.empty():
                self.message = result
                self.set_state("done")

    def set_state(self, state):
        self.state, self.state_t = state, 0.0

    # ---------- animação ----------
    def tick(self):
        dt = 1 / 30
        self.state_t += dt
        self.phase += dt
        if self.state == "morph_in" and self.state_t >= 0.9:
            self.set_state("working")
        elif self.state == "done" and self.state_t >= 2.6 and self.jobs.empty():
            self.set_state("morph_out")
        elif self.state == "morph_out" and self.state_t >= 0.9:
            self.set_state("idle")
            self.message = "Arraste um vídeo ou áudio aqui" if self.dnd else \
                "Clique aqui para escolher um vídeo"
        self.draw()
        self.after(33, self.tick)

    def draw(self):
        c = self.canvas
        c.delete("all")
        cw, ch = W, H - 44
        cy = ch / 2 - 14
        if self.state == "idle":
            mix = 0.0
        elif self.state == "morph_in":
            mix = ease(self.state_t / 0.9)
        elif self.state == "morph_out":
            mix = 1 - ease(self.state_t / 0.9)
        else:
            mix = 1.0
        if mix < 0.5:
            self.draw_film(c, cw, cy, 1 - mix * 2)
        else:
            self.draw_wave(c, cw, cy, (mix - 0.5) * 2)
        c.create_text(cw / 2, ch - 34, text=self.message, fill=CREAM,
                      font=("Segoe UI", 11), width=cw - 40)

    def draw_film(self, c, cw, cy, k):
        """Fita de filme rolando; k (0..1) achata a fita para a metamorfose."""
        h = 120 * k
        if h < 2:
            c.create_line(30, cy, cw - 30, cy, fill=CREAM, width=3)
            return
        top, bot = cy - h / 2, cy + h / 2
        c.create_rectangle(0, top, cw, bot, fill=INK, outline="")
        frame_w, gap = 92, 14
        offset = -(self.phase * 40) % (frame_w + gap)
        x = offset - (frame_w + gap)
        hole_h = max(2, 10 * k)
        while x < cw:
            for i in range(5):
                hx = x + 6 + i * 19
                c.create_rectangle(hx, top + 5 * k, hx + 10, top + 5 * k + hole_h,
                                   fill=CREAM, outline="")
                c.create_rectangle(hx, bot - 5 * k - hole_h, hx + 10, bot - 5 * k,
                                   fill=CREAM, outline="")
            ft, fb = top + 22 * k, bot - 22 * k
            if fb - ft > 2:
                c.create_rectangle(x, ft, x + frame_w, fb, fill=ORANGE, outline="")
                mx, my, s = x + frame_w / 2, (ft + fb) / 2, 12 * k
                c.create_polygon(mx - s * 0.7, my - s, mx - s * 0.7, my + s, mx + s, my,
                                 fill=CREAM, outline="")
            x += frame_w + gap

    def draw_wave(self, c, cw, cy, k):
        """Forma de onda; barras à esquerda do progresso ficam claras."""
        n = len(self.bars)
        span = cw - 80
        step = span / n
        done_x = 40 + span * (self.progress if self.state != "morph_out" else 1)
        for i, base in enumerate(self.bars):
            wobble = 0.55 + 0.45 * math.sin(self.phase * 5 + i * 0.7)
            if self.state == "done" or self.state == "morph_out":
                wobble = 0.6 + 0.1 * math.sin(self.phase * 2 + i * 0.5)
            amp = 58 * base * wobble * k + 2
            x = 40 + i * step + step / 2
            color = CREAM if x <= done_x else ORANGE_DARK
            c.create_line(x, cy - amp, x, cy + amp, fill=color, width=max(2, step * 0.55),
                          capstyle="round")
        if self.state == "working":
            c.create_text(cw / 2, cy + 82, text=f"{self.progress * 100:.0f}%", fill=CREAM,
                          font=("Segoe UI", 10, "bold"))


if __name__ == "__main__":
    App().mainloop()
