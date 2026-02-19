import os
import sys
import shutil
import json

root     = sys.argv[1]
build_dir = sys.argv[2]
dist_dir  = sys.argv[3]
work_dir  = os.path.join(build_dir, "work")
spec_dir  = build_dir
exe_name  = "DiscordBotDashboard"
main_py   = os.path.join(root, "main.py")

print("")

if not os.path.exists(main_py):
    print("  ERROR: main.py not found at: " + main_py)
    sys.exit(1)

ffmpeg_path = None
ffmpeg_which = shutil.which("ffmpeg")
if ffmpeg_which:
    ffmpeg_path = ffmpeg_which
else:
    for candidate in [
        os.path.join(root, "ffmpeg.exe"),
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
        r"C:\tools\ffmpeg\bin\ffmpeg.exe",
    ]:
        if os.path.exists(candidate):
            ffmpeg_path = candidate
            break

if ffmpeg_path:
    print("  FFmpeg  ................  " + ffmpeg_path)
else:
    print("  FFmpeg  ................  NOT FOUND (music disabled)")

args = [
    sys.executable, "-m", "PyInstaller",
    "--noconfirm",
    "--onefile",
    "--windowed",
    "--name", exe_name,
    "--distpath", dist_dir,
    "--workpath", work_dir,
    "--specpath", spec_dir,
    "--hidden-import", "discord",
    "--hidden-import", "discord.ext.commands",
    "--hidden-import", "discord.ext.tasks",
    "--hidden-import", "discord.opus",
    "--hidden-import", "discord.voice_client",
    "--hidden-import", "discord.player",
    "--hidden-import", "discord.gateway",
    "--hidden-import", "discord.http",
    "--hidden-import", "yt_dlp",
    "--hidden-import", "yt_dlp.extractor",
    "--hidden-import", "yt_dlp.postprocessor",
    "--hidden-import", "yt_dlp.downloader",
    "--hidden-import", "yt_dlp.utils",
    "--hidden-import", "nacl",
    "--hidden-import", "nacl.secret",
    "--hidden-import", "nacl.public",
    "--hidden-import", "psutil",
    "--hidden-import", "tkinter",
    "--hidden-import", "tkinter.ttk",
    "--hidden-import", "tkinter.scrolledtext",
    "--hidden-import", "tkinter.messagebox",
    "--hidden-import", "asyncio",
    "--hidden-import", "threading",
    "--hidden-import", "json",
    "--hidden-import", "traceback",
    "--collect-all", "discord",
    "--collect-all", "yt_dlp",
    "--collect-all", "nacl",
    "--collect-all", "psutil",
]

for fname in ("musicManager.py", "administrationManager.py", "i18n.py", "bot_config.json"):
    fpath = os.path.join(root, fname)
    if os.path.exists(fpath):
        args += ["--add-data", fpath + ";."]
        print("  " + fname.ljust(30) + "  included")
    else:
        print("  " + fname.ljust(30) + "  not found (skipped)")

if ffmpeg_path:
    args += ["--add-binary", ffmpeg_path + ";."]

args.append(main_py)

out_file = os.path.join(build_dir, "_build_args.json")
with open(out_file, "w", encoding="utf-8") as f:
    json.dump(args, f)

print("")
print("  Configuration saved to: " + out_file)