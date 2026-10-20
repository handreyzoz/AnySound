"""AnySound - converte vídeos em áudio (MP3, WAV, ...) em um único .exe."""
import os
import re
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import imageio_ffmpeg

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    BaseTk = TkinterDnD.Tk
except ImportError:
    DND_FILES, BaseTk = None, tk.Tk

FORMATS = {
    "mp3": ["-c:a", "libmp3lame"],
    "wav": ["-c:a", "pcm_s16le"],
    "flac": ["-c:a", "flac"],
    "ogg": ["-c:a", "libvorbis"],
    "m4a": ["-c:a", "aac"],
    "opus": ["-c:a", "libopus"],
}
BITRATES = ["320k", "256k", "192k", "128k", "96k"]
LOSSLESS = {"wav", "flac"}
VIDEO_TYPES = [
    ("Vídeos", "*.mp4 *.mkv *.avi *.mov *.webm *.flv *.wmv *.m4v *.mpg *.mpeg *.3gp *.ts *.m2ts *.mts *.m2t *.tsv *.trp"),
    ("MPEG-TS", "*.ts *.m2ts *.mts *.m2t *.tsv *.trp"),
    ("Todos os arquivos", "*.*"),
]
VIDEO_EXTS = {"." + e.lstrip("*.") for e in VIDEO_TYPES[0][1].split()}
NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


def ffmpeg_exe():
    return imageio_ffmpeg.get_ffmpeg_exe()


def parse_time(text):
    h, m, s = text.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


class App(BaseTk):
    def __init__(self):
        super().__init__()
        self.title("AnySound - Vídeo para Áudio")
        self.geometry("620x440")
        self.minsize(520, 380)
        self.files = []
        self.outdir = tk.StringVar(value="")
        self.fmt = tk.StringVar(value="mp3")
        self.bitrate = tk.StringVar(value="192k")
        self.busy = False

        pad = {"padx": 10, "pady": 5}
        top = ttk.Frame(self)
        top.pack(fill="x", **pad)
        ttk.Button(top, text="Adicionar vídeos...", command=self.add_files).pack(side="left")
        ttk.Button(top, text="Limpar", command=self.clear).pack(side="left", padx=5)

        self.listbox = tk.Listbox(self, selectmode="extended")
        self.listbox.pack(fill="both", expand=True, **pad)
        if DND_FILES:
            self.listbox.insert("end", "Arraste vídeos ou pastas para cá...")
            self.listbox.itemconfigure(0, foreground="gray")
            self.drop_target_register(DND_FILES)
            self.dnd_bind("<<Drop>>", self.on_drop)

        opts = ttk.Frame(self)
        opts.pack(fill="x", **pad)
        ttk.Label(opts, text="Formato:").pack(side="left")
        cb = ttk.Combobox(opts, textvariable=self.fmt, values=list(FORMATS), state="readonly", width=6)
        cb.pack(side="left", padx=5)
        cb.bind("<<ComboboxSelected>>", lambda e: self.update_bitrate())
        ttk.Label(opts, text="Qualidade:").pack(side="left", padx=(15, 0))
        self.br_box = ttk.Combobox(opts, textvariable=self.bitrate, values=BITRATES, state="readonly", width=6)
        self.br_box.pack(side="left", padx=5)

        out = ttk.Frame(self)
        out.pack(fill="x", **pad)
        ttk.Label(out, text="Salvar em:").pack(side="left")
        ttk.Entry(out, textvariable=self.outdir).pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(out, text="...", width=3, command=self.pick_dir).pack(side="left")
        ttk.Label(self, text="(vazio = mesma pasta do vídeo)", foreground="gray").pack(anchor="w", padx=10)

        self.progress = ttk.Progressbar(self, maximum=100)
        self.progress.pack(fill="x", **pad)
        self.status = ttk.Label(self, text="Pronto.")
        self.status.pack(anchor="w", padx=10)
        self.convert_btn = ttk.Button(self, text="Converter", command=self.start)
        self.convert_btn.pack(pady=10)

    def update_bitrate(self):
        self.br_box.configure(state="disabled" if self.fmt.get() in LOSSLESS else "readonly")

    def add_paths(self, paths):
        if self.busy:
            return
        if not self.files:
            self.listbox.delete(0, "end")
        for f in paths:
            f = os.path.normpath(f)
            if f not in self.files:
                self.files.append(f)
                self.listbox.insert("end", f)

    def add_files(self):
        self.add_paths(filedialog.askopenfilenames(title="Escolha os vídeos", filetypes=VIDEO_TYPES))

    def on_drop(self, event):
        found = []
        for p in self.tk.splitlist(event.data):
            if os.path.isdir(p):
                for root, _, names in os.walk(p):
                    found += [os.path.join(root, n) for n in sorted(names)
                              if os.path.splitext(n)[1].lower() in VIDEO_EXTS]
            elif os.path.isfile(p):
                found.append(p)
        self.add_paths(found)

    def clear(self):
        if not self.busy:
            self.files.clear()
            self.listbox.delete(0, "end")

    def pick_dir(self):
        d = filedialog.askdirectory()
        if d:
            self.outdir.set(d)

    def set_status(self, text, pct=None):
        self.after(0, lambda: (self.status.configure(text=text),
                               pct is not None and self.progress.configure(value=pct)))

    def start(self):
        if self.busy:
            return
        if not self.files:
            messagebox.showwarning("AnySound", "Adicione pelo menos um vídeo.")
            return
        self.busy = True
        self.convert_btn.configure(state="disabled")
        threading.Thread(target=self.run, daemon=True).start()

    def run(self):
        fmt, errors = self.fmt.get(), []
        total = len(self.files)
        for i, src in enumerate(list(self.files)):
            name = os.path.splitext(os.path.basename(src))[0]
            dest_dir = self.outdir.get() or os.path.dirname(src)
            dest = os.path.join(dest_dir, f"{name}.{fmt}")
            n = 1
            while os.path.exists(dest):
                dest = os.path.join(dest_dir, f"{name} ({n}).{fmt}")
                n += 1
            self.set_status(f"[{i + 1}/{total}] Convertendo {os.path.basename(src)}...")
            try:
                self.convert(src, dest, fmt, i, total)
            except Exception as e:
                errors.append(f"{os.path.basename(src)}: {e}")
        self.set_status("Concluído!" if not errors else "Concluído com erros.", 100)
        self.after(0, lambda: self.finish(errors))

    def convert(self, src, dest, fmt, index, total):
        cmd = [ffmpeg_exe(), "-y", "-hide_banner", "-fflags", "+genpts+discardcorrupt",
               "-i", src, "-vn", "-sn", "-dn", "-map", "0:a:0", *FORMATS[fmt]]
        if fmt not in LOSSLESS:
            cmd += ["-b:a", self.bitrate.get()]
        cmd.append(dest)
        proc = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                stdin=subprocess.DEVNULL, universal_newlines=True,
                                encoding="utf-8", errors="replace", creationflags=NO_WINDOW)
        duration, tail = None, []
        for line in iter(proc.stderr.readline, ""):
            tail = (tail + [line.strip()])[-5:]
            if duration is None:
                m = re.search(r"Duration: (\d+:\d+:[\d.]+)", line)
                if m:
                    duration = parse_time(m.group(1))
            m = re.search(r"time=(\d+:\d+:[\d.]+)", line)
            if m and duration:
                frac = min(parse_time(m.group(1)) / duration, 1)
                self.set_status(self.status.cget("text"), (index + frac) / total * 100)
        if proc.wait() != 0:
            if os.path.exists(dest):
                os.remove(dest)
            raise RuntimeError(tail[-1] if tail else "falha no ffmpeg")

    def finish(self, errors):
        self.busy = False
        self.convert_btn.configure(state="normal")
        if errors:
            messagebox.showerror("AnySound", "Alguns arquivos falharam:\n\n" + "\n".join(errors))
        else:
            messagebox.showinfo("AnySound", "Conversão concluída!")


if __name__ == "__main__":
    App().mainloop()
