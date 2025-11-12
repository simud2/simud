import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Optional  # ✅ aggiunto
import yt_dlp

# ====== CONFIGURAZIONE ======
CHANNEL_URL = "https://www.youtube.com/@skysport/videos"
MAX_VIDEOS = 30
DESKTOP = Path.home() / "Desktop"
HIGHLIGHTS_DIR = Path("Highlights")
M3U8_PATH = DESKTOP / "SimudLights.m3u8"

GITHUB_BASE_URL = "https://github.com/simud2/simud/blob/main/Highlights"
LOGO_URL = "https://www.chefstudio.it/img/blog/logo-serie-a/logo-serie-a.jpg"


def check_yt_dlp_version():
    try:
        print(f"yt-dlp versione: {yt_dlp.__version__}  (aggiorna con: yt-dlp -U)\n")
    except Exception:
        pass


def make_filename(title: str) -> str:
    nfkd = unicodedata.normalize("NFKD", title)
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii")
    lower = ascii_str.lower()
    only_alnum = re.sub(r"[^a-z0-9]+", "", lower)
    trimmed = only_alnum[:80] if only_alnum else "video"
    return f"{trimmed}.mp4"


def get_recent_videos():
    ydl_opts = {
        "quiet": True,
        "extract_flat": True,
        "playlist_items": f"1:{MAX_VIDEOS}",
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(CHANNEL_URL, download=False)
        entries = info.get("entries", [])
        return [(e.get("title", ""), e.get("url")) for e in entries if e.get("url")]


def is_highlights(title: str) -> bool:
    return "highlights" in (title or "").lower()


def download_video(title: str, url: str, out_dir: Path) -> Optional[str]:
    """Scarica il video nella cartella Highlights e restituisce il percorso locale."""
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = make_filename(title)
    output_path = out_dir / filename

    if output_path.exists():
        print(f"⚠️  Il file '{filename}' esiste già, salto il download.")
        return str(output_path)

    ydl_opts = {
        "outtmpl": str(output_path),
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
        "merge_output_format": "mp4",
        "extractor_args": {"youtube": {"player_client": ["android"]}},
        "quiet": False,
        "noplaylist": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print(f"✅ Scaricato: {title} -> {filename}")
        return str(output_path)
    except Exception as e:
        print(f"❌ Errore nel download di '{title}': {e}")
        return None


def write_m3u8(entries, m3u8_path: Path):
    with open(m3u8_path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for title, local_path in entries:
            filename = os.path.basename(local_path)
            remote_url = f"{GITHUB_BASE_URL}/{filename}"
            f.write(f'#EXTINF:-1 tvg-id="1" tvg-logo="{LOGO_URL}" group-title="Highlights", {title}\n')
            f.write(f"{remote_url}\n")
    print(f"\n🎵 Playlist creata: {m3u8_path}")


def main():
    print("🔍 Ricerca Highlights su Sky Sport...")
    check_yt_dlp_version()

    videos = get_recent_videos()
    if not videos:
        print("❌ Nessun video trovato.")
        sys.exit(1)

    highlights = [(t, u) for (t, u) in videos if is_highlights(t)]
    print(f"Trovati {len(highlights)} video con 'Highlights' nel titolo.\n")

    downloaded = []
    for title, url in highlights:
        print(f"⬇️  Download: {title}")
        path = download_video(title, url, HIGHLIGHTS_DIR)
        if path:
            downloaded.append((title, path))

    if not downloaded:
        print("⚠️ Nessun video scaricato.")
        sys.exit(0)

    write_m3u8(downloaded, M3U8_PATH)

    print("\n✅ Operazione completata!")
    print(f"📂 Cartella: {HIGHLIGHTS_DIR.resolve()}")
    print(f"📄 Playlist: {M3U8_PATH}")


if __name__ == "__main__":
    main()
