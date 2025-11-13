import os
import sys
import re
from pathlib import Path

# ✅ Percorso forzato per yt_dlp (installazione Microsoft Store)
YT_DLP_PATH = r"C:\Users\cambr\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\LocalCache\local-packages\Python311\site-packages"
if YT_DLP_PATH not in sys.path:
    sys.path.insert(0, YT_DLP_PATH)

try:
    import yt_dlp
    print("✅ Modulo yt_dlp importato correttamente.\n")
except ImportError:
    print("❌ yt-dlp non trovato.")
    sys.exit(1)

# === CONFIG ===
CHANNEL_URL = "https://www.youtube.com/@skysport/videos"
M3U8_PATH = os.path.join(Path.home(), "Desktop", "SimudLights_HLS.m3u8")
MAX_VIDEOS = 50
LOGO_URL = "https://www.chefstudio.it/img/blog/logo-serie-a/logo-serie-a.jpg"

TEAMS = [
    "Atalanta", "Bologna", "Cagliari", "Como", "Cremonese",
    "Fiorentina", "Genoa", "Hellas Verona", "Inter", "Juventus",
    "Lazio", "Lecce", "Milan", "Napoli", "Parma", "Pisa",
    "Roma", "Sassuolo", "Torino", "Udinese"
]


def get_videos():
    """Estrae gli ultimi video dal canale YouTube"""
    ydl_opts = {
        "quiet": True,
        "extract_flat": True,
        "playlist_items": f"1:{MAX_VIDEOS}",
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(CHANNEL_URL, download=False)
        return [
            (entry["title"], entry["url"])
            for entry in info.get("entries", [])
            if entry.get("url")
        ]


def get_hls_url(url):
    """Estrae il link HLS (manifesto .m3u8) da un video YouTube"""
    try:
        opts = {
            "quiet": True,
            "skip_download": True,
            "format": "best[protocol^=m3u8]",
            "noplaylist": True,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if "url" in info and "m3u8" in info["url"]:
                return info["url"]

            # Cerca nei formati alternativi
            for f in info.get("formats", []):
                if "m3u8" in (f.get("url") or ""):
                    return f["url"]

    except Exception as e:
        print(f"⚠️ Errore durante l'estrazione HLS: {e}")

    return None


def clean_title(title):
    """Rimuove solo | e : dai titoli, mantiene i trattini e normalizza gli spazi"""
    title = title.replace("|", " ").replace(":", " ")
    title = re.sub(r'\s+', ' ', title)  # rimuove spazi doppi
    return title.strip()


def create_m3u8(entries):
    """Crea la playlist M3U8"""
    with open(M3U8_PATH, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for i, (title, url) in enumerate(entries, start=1):
            readable_title = clean_title(title)
            tvg_id = f"simud{i}"
            f.write(
                f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{readable_title}" '
                f'tvg-logo="{LOGO_URL}" group-title="Highlights", {readable_title}\n'
            )
            f.write(f"{url}\n")

    print(f"\n🎵 Playlist M3U8 creata con {len(entries)} voci:")
    print(f"📁 {M3U8_PATH}\n")


def main():
    print("\n🏁 Inizio estrazione HLS da Sky Sport (YouTube)\n")
    videos = get_videos()
    if not videos:
        print("❌ Nessun video trovato.")
        sys.exit(1)

    filtered = [
        (title, url)
        for title, url in videos
        if "highlight" in title.lower()
        and any(team.lower() in title.lower() for team in TEAMS)
    ]

    print(f"🎯 Trovati {len(filtered)} video validi.\n")

    hls_streams = []
    for title, url in filtered:
        print(f"▶️  Estrazione HLS: {title}")
        hls = get_hls_url(url)
        if hls:
            print("   🌐 OK:", hls.split("?")[0])
            hls_streams.append((title, hls))
        else:
            print("   ⚠️ Nessun HLS trovato per:", title)

    if hls_streams:
        create_m3u8(hls_streams)
        print("✅ Completato con successo!")
    else:
        print("⚠️ Nessun flusso HLS disponibile.")


if __name__ == "__main__":
    main()
