#!/usr/bin/env python3
"""Simple macOS GUI for the FairPlay IPA decryptor.

Wraps ``decrypt.py`` in a Tk window: pick an encrypted IPA, a credential
file and an output path, then decrypt while the tool's progress lines
stream into a log. Uses tkinter, which ships with the python.org macOS
build; no third-party dependencies.
"""

from __future__ import annotations

import platform
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

ROOT = Path(__file__).resolve().parent
TRANSFORM = ROOT / "transform"

IS_MACOS = platform.system() == "Darwin"


class DecryptRunner:
    """Runs decrypt.py as a subprocess and streams its output to a queue."""

    def __init__(self) -> None:
        self.process: subprocess.Popen | None = None
        self.lines: queue.Queue[str | None] = queue.Queue()
        self.returncode: int | None = None

    def start(self, ipa: Path, output: Path, credential: Path) -> None:
        command = [
            sys.executable,
            str(ROOT / "decrypt.py"),
            str(ipa),
            str(output),
            "--credential",
            str(credential),
        ]
        self.process = subprocess.Popen(
            command,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        threading.Thread(target=self._drain, daemon=True).start()

    def _drain(self) -> None:
        assert self.process and self.process.stdout
        for line in self.process.stdout:
            self.lines.put(line.rstrip("\n"))
        self.returncode = self.process.wait()
        self.lines.put(None)

    def cancel(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.lines.put(None)


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.runner = DecryptRunner()
        self.busy = False
        root.title("FairPlay Decrypt")
        root.minsize(620, 420)

        outer = ttk.Frame(root, padding=16)
        outer.pack(fill=tk.BOTH, expand=True)

        self.ipa_var = tk.StringVar()
        self.credential_var = tk.StringVar(value=str(ROOT / "credential.bin"))
        self.output_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready.")

        def picker_row(label: str, variable: tk.StringVar, kind: str) -> None:
            ttk.Label(outer, text=label).grid(sticky="w", pady=(0, 4))

            def choose() -> None:
                if kind == "save":
                    path = filedialog.asksaveasfilename(
                        defaultextension=".ipa",
                        initialfile="decrypted.ipa",
                        title="Decrypted output",
                    )
                elif kind == "credential":
                    path = filedialog.askopenfilename(title="credential.bin")
                else:
                    path = filedialog.askopenfilename(
                        title="Encrypted IPA",
                        filetypes=[("IPA", "*.ipa"), ("All files", "*")],
                    )
                if path:
                    variable.set(path)

            row = ttk.Frame(outer)
            row.grid(sticky="ew", pady=(0, 8))
            row.columnconfigure(0, weight=1)
            ttk.Entry(row, textvariable=variable).pack(
                side=tk.LEFT, fill=tk.X, expand=True
            )
            ttk.Button(row, text="Choose…", command=choose).pack(side=tk.LEFT, padx=(6, 0))

        picker_row("Encrypted IPA", self.ipa_var, "open")
        picker_row("Credential (credential.bin)", self.credential_var, "credential")
        picker_row("Decrypted output", self.output_var, "save")

        buttons = ttk.Frame(outer)
        buttons.grid(sticky="ew", pady=(4, 8))
        self.decrypt_button = ttk.Button(buttons, text="Decrypt", command=self.on_decrypt)
        self.decrypt_button.pack(side=tk.LEFT)
        self.cancel_button = ttk.Button(
            buttons, text="Cancel", command=self.on_cancel, state=tk.DISABLED
        )
        self.cancel_button.pack(side=tk.LEFT, padx=(8, 0))

        log_frame = ttk.LabelFrame(outer, text="Progress", padding=6)
        log_frame.grid(sticky="nsew", pady=(0, 8))
        outer.rowconfigure(log_frame.grid_info()["row"], weight=1)
        self.log = tk.Text(
            log_frame, height=10, wrap=tk.WORD, state=tk.DISABLED, undo=False
        )
        self.log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(log_frame, command=self.log.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log.configure(yscrollcommand=scrollbar.set)

        ttk.Label(outer, textvariable=self.status_var).grid(sticky="w")

        if not TRANSFORM.exists():
            self.append_log(
                "'transform' is not built yet.\n"
                "Run `make` in the repository directory first "
                "(Xcode Command Line Tools: xcode-select --install).\n"
            )
            self.status_var.set("Not ready: run `make` to build 'transform'.")

    def append_log(self, text: str) -> None:
        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, text if text.endswith("\n") else text + "\n")
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)

    def validate(self) -> tuple[Path, Path, Path] | None:
        ipa = Path(self.ipa_var.get())
        credential = Path(self.credential_var.get())
        output = Path(self.output_var.get())
        if not ipa.is_file():
            messagebox.showerror("FairPlay Decrypt", "Encrypted IPA not found.")
            return None
        if not credential.is_file():
            messagebox.showerror("FairPlay Decrypt", "credential.bin not found.")
            return None
        if output.exists():
            messagebox.showerror(
                "FairPlay Decrypt", "Output already exists; never overwrite it."
            )
            return None
        if output.resolve() == ipa.resolve():
            messagebox.showerror("FairPlay Decrypt", "Input and output must differ.")
            return None
        return ipa, output, credential

    def on_decrypt(self) -> None:
        if not TRANSFORM.exists():
            messagebox.showerror(
                "FairPlay Decrypt",
                "'transform' is missing. Build it first: run `make` in the "
                "repository directory.",
            )
            return
        paths = self.validate()
        if paths is None:
            return
        ipa, output, credential = paths
        self.busy = True
        self.decrypt_button.configure(state=tk.DISABLED)
        self.cancel_button.configure(state=tk.NORMAL)
        self.append_log(
            f"$ decrypt.py {ipa.name} {output.name} --credential {credential.name}"
        )
        self.runner.start(ipa, output, credential)
        self.root.after(200, self.poll)

    def on_cancel(self) -> None:
        self.runner.cancel()
        self.status_var.set("Cancelling…")

    def poll(self) -> None:
        finished = False
        while True:
            try:
                item = self.runner.lines.get_nowait()
            except queue.Empty:
                break
            if item is None:
                finished = True
                break
            self.append_log(item)
        if finished:
            self.busy = False
            self.decrypt_button.configure(state=tk.NORMAL)
            self.cancel_button.configure(state=tk.DISABLED)
            code = self.runner.returncode
            if code == 0:
                output = Path(self.output_var.get())
                self.status_var.set(f"Done: {output}")
                self.append_log("Decryption finished.")
                if IS_MACOS:
                    subprocess.Popen(["open", "-R", str(output)])
            elif code is None:
                self.status_var.set("Cancelled.")
                self.append_log("Cancelled.")
            else:
                self.status_var.set(f"Failed (exit {code}).")
        elif self.busy:
            self.root.after(200, self.poll)


def main() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
