import platform
import shutil
import subprocess


def play(path: str) -> None:
    system = platform.system()

    if system == "Darwin":
        subprocess.run(["afplay", path], check=True)
        return

    if system == "Windows":
        import ctypes  # type: ignore[attr-defined]

        winmm = ctypes.windll.winmm  # type: ignore[attr-defined]
        winmm.mciSendStringW(f'open "{path}" type mpegvideo alias tts_playback', None, 0, None)
        winmm.mciSendStringW("play tts_playback wait", None, 0, None)
        winmm.mciSendStringW("close tts_playback", None, 0, None)
        return

    for player in ("ffplay", "mpv", "mpg123", "paplay", "aplay"):
        if shutil.which(player):
            if player == "ffplay":
                subprocess.run(
                    [player, "-nodisp", "-autoexit", "-loglevel", "quiet", path], check=True
                )
            else:
                subprocess.run([player, path], check=True)
            return

    raise RuntimeError(
        "No audio player found. Install one of: ffplay (ffmpeg), mpv, mpg123, paplay, or aplay."
    )
