#!/usr/bin/env python3
"""
build.py — Clean build script for AzroksRepublic.exe

Shows a progress bar and writes a human-readable log to build/build_<timestamp>.log
"""

import subprocess, sys, os, re, datetime, pathlib, shutil

# ── ANSI colour helpers ────────────────────────────────────────────────────────
RESET  = "\x1b[0m"
BOLD   = "\x1b[1m"
DIM    = "\x1b[2m"
GREEN  = "\x1b[32m"
YELLOW = "\x1b[33m"
CYAN   = "\x1b[36m"
RED    = "\x1b[31m"

BAR_W = 42   # characters wide for the progress fill

def enable_ansi():
    """Turn on ANSI escape-code processing in the Windows console."""
    if sys.platform == "win32":
        import ctypes
        k32 = ctypes.windll.kernel32
        k32.SetConsoleMode(k32.GetStdHandle(-11), 7)

def draw_bar(pct: int, label: str):
    filled = int(BAR_W * pct / 100)
    bar    = "█" * filled + "░" * (BAR_W - filled)
    sys.stdout.write(f"\r  {CYAN}[{bar}]{RESET}  {pct:3d}%  {label:<38}")
    sys.stdout.flush()

def print_step(symbol: str, colour: str, msg: str):
    print(f"  {colour}{symbol}{RESET}  {msg}")


# ── PyInstaller phase map ──────────────────────────────────────────────────────
# Each entry: (regex to match in raw output, target %, human label)
PHASES = [
    (r"Running Analysis",                      10, "Analyzing source"),
    (r"Analyzing modules for base_library",    20, "Scanning stdlib"),
    (r"Processing standard module hook",       28, "Processing hooks"),
    (r"Processing module hooks \(post",        38, "Post-processing hooks"),
    (r"Performing binary vs\. data",           45, "Classifying binaries"),
    (r"Looking for dynamic libraries",         50, "Collecting DLLs"),
    (r"Building PYZ \(ZlibArchive\).*\.pyz$", 58, "Compressing bytecode"),
    (r"PYZ.*completed successfully",           63, "Bytecode archive ready"),
    (r"Building PKG \(CArchive\)",             68, "Packaging application"),
    (r"PKG.*completed successfully",           82, "Package assembled"),
    (r"Building EXE from",                     86, "Assembling executable"),
    (r"Copying bootloader",                    90, "Copying bootloader"),
    (r"Copying icon",                          93, "Embedding icon"),
    (r"Appending PKG archive to EXE",          96, "Appending archive"),
    (r"Build complete",                       100, "Done!"),
]


def clean_log_line(raw: str) -> str:
    """
    Turn a raw PyInstaller line into something a human would want to read.

    Input:  '5137 INFO: Looking for ctypes DLLs'
    Output: 'Looking for ctypes DLLs'
    """
    line = raw.strip()
    if not line:
        return ""

    # Strip leading millisecond timestamp ("1234 ")
    line = re.sub(r"^\d+\s+", "", line)

    # Map severity prefixes to readable tags
    line = re.sub(r"^INFO:\s*",        "",          line)
    line = re.sub(r"^DEPRECATION:\s*", "[notice]  ", line)
    line = re.sub(r"^WARNING:\s*",     "[warning] ", line)
    line = re.sub(r"^ERROR:\s*",       "[error]   ", line)
    line = re.sub(r"^CRITICAL:\s*",    "[CRITICAL] ", line)

    return line


def run():
    enable_ansi()
    root = pathlib.Path(__file__).parent

    # ── Header ─────────────────────────────────────────────────────────────────
    width = 60
    now   = datetime.datetime.now()
    print(f"\n{BOLD}{'─' * width}{RESET}")
    print(f"  {BOLD}Azrok's Republic{RESET}  —  Build Script")
    print(f"  {DIM}{now.strftime('%Y-%m-%d   %H:%M:%S')}{RESET}")
    print(f"{BOLD}{'─' * width}{RESET}\n")

    # ── Log file setup ─────────────────────────────────────────────────────────
    build_dir = root / "build"
    build_dir.mkdir(exist_ok=True)
    log_path  = build_dir / f"build_{now.strftime('%Y-%m-%d_%H-%M-%S')}.log"

    log_lines = [
        "Azrok's Republic — Build Log",
        f"Started : {now.isoformat()}",
        "=" * width,
        "",
    ]

    def log(line: str):
        log_lines.append(line)

    def flush_log(extra_lines=None):
        if extra_lines:
            log_lines.extend(extra_lines)
        log_path.write_text("\n".join(log_lines), encoding="utf-8")

    # ── Step 1: Generate icon ──────────────────────────────────────────────────
    print_step("→", YELLOW, "Generating icon …")
    r = subprocess.run(
        [sys.executable, str(root / "make_icon.py")],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        print_step("✗", RED, "Icon generation failed.")
        print(f"\n{r.stderr}")
        flush_log(["[error]  Icon generation failed", r.stderr])
        sys.exit(1)

    icon_info = r.stdout.strip()
    print_step("✓", GREEN, icon_info)
    log(f"[ok]     {icon_info}")
    log("")

    # ── Step 2: PyInstaller ────────────────────────────────────────────────────
    print()
    draw_bar(0, "Starting PyInstaller …")
    log(f"{'─' * width}")
    log("PyInstaller output")
    log(f"{'─' * width}")

    current_pct   = 0
    current_label = "Starting …"
    compiled = [(re.compile(pat), pct, lbl) for pat, pct, lbl in PHASES]

    proc = subprocess.Popen(
        [sys.executable, "-m", "PyInstaller", "--clean",
         str(root / "AzroksRepublic.spec")],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=str(root),
    )

    for raw_line in proc.stdout:
        clean = clean_log_line(raw_line)
        if clean:
            log(clean)

        for pattern, pct, label in compiled:
            if pct > current_pct and pattern.search(raw_line):
                current_pct   = pct
                current_label = label
                draw_bar(current_pct, current_label)
                break

    proc.wait()
    print()   # end of progress-bar line

    if proc.returncode != 0:
        print()
        print_step("✗", RED, f"PyInstaller failed (exit {proc.returncode}).")
        print(f"  {DIM}See log for details: {log_path}{RESET}\n")
        flush_log([f"", f"[error]  PyInstaller exited with code {proc.returncode}"])
        sys.exit(1)

    # ── Step 3: Copy to build/ ─────────────────────────────────────────────────
    src      = root / "dist"  / "AzroksRepublic.exe"
    dest     = root / "build" / "AzroksRepublic.exe"
    shutil.copy2(src, dest)
    size_mb  = dest.stat().st_size / 1_048_576
    log("")
    log(f"[ok]     Copied to {dest}  ({size_mb:.1f} MB)")

    # ── Write final log ────────────────────────────────────────────────────────
    finished = datetime.datetime.now()
    elapsed  = (finished - now).total_seconds()
    flush_log([
        "",
        "=" * width,
        f"Finished : {finished.isoformat()}",
        f"Elapsed  : {elapsed:.1f}s",
    ])

    # ── Summary ────────────────────────────────────────────────────────────────
    print()
    print_step("✓", GREEN, f"{BOLD}Build successful!{RESET}  ({elapsed:.0f}s)")
    print(f"  {DIM}Executable : {dest}  ({size_mb:.1f} MB){RESET}")
    print(f"  {DIM}Log        : {log_path}{RESET}")
    print(f"\n{BOLD}{'─' * width}{RESET}\n")


if __name__ == "__main__":
    run()
