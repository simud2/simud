import requests
import json
import re
from playwright.sync_api import sync_playwright
import urllib.parse
import logging

# Configura logging
logging.basicConfig(
    filename="simudflix_errors.log",
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# TMDb API key
API_KEY = "8265bd1679663a7ea12ac168da84d2e8"
BASE_API_URL = "https://api.themoviedb.org/3"
VIXSRC_URL = "https://vixsrc.to"

# Endpoints per film
ENDPOINTS = {
    "trending": "trending/movie/day",
    "nowPlaying": "movie/now_playing",
    "popularMovies": "movie/popular",
}

def fetch_movies(endpoint, pages=3):
    """Fetch fino a 50 film da TMDb API."""
    movies = []
    for page in range(1, pages + 1):
        url = f"{BASE_API_URL}/{endpoint}?api_key={API_KEY}&language=it-IT&page={page}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            movies.extend(data.get("results", [])[:50 - len(movies)])
            if len(movies) >= 50:
                break
        except requests.RequestException as e:
            print(f"Errore fetch {endpoint} pagina {page}: {e}")
            logging.error(f"Errore fetch {endpoint} pagina {page}: {e}")
    return movies[:50]

def fetch_movie_details(movie_id):
    """Fetch dettagli extra (generi, poster) per metadata M3U8."""
    try:
        url = f"{BASE_API_URL}/movie/{movie_id}?api_key={API_KEY}&language=it-IT"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Errore dettagli film {movie_id}: {e}")
        return {}

def get_stream_url(movie_id, is_movie=True):
    """Estrae URL stream da vixsrc.to usando Playwright."""
    vixsrc_url = f"{VIXSRC_URL}/{'movie' if is_movie else 'tv'}/{movie_id}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                extra_http_headers={"Referer": VIXSRC_URL}
            )
            page = context.new_page()
            print(f"Tentativo Playwright per {movie_id}: {vixsrc_url}")
            page.goto(vixsrc_url, wait_until="networkidle", timeout=30000)

            # Estrai parametri playlist
            playlist_data = page.evaluate("""
                () => {
                    if (typeof window.masterPlaylist !== 'undefined' && window.masterPlaylist.params) {
                        return {
                            url: window.masterPlaylist.url,
                            params: window.masterPlaylist.params,
                            canPlayFHD: window.canPlayFHD === true
                        };
                    }
                    return null;
                }
            """)

            browser.close()

            if not playlist_data or not playlist_data.get("url"):
                print(f"Nessun dato playlist per {movie_id}")
                return None

            playlist_url = playlist_data["url"]
            params = playlist_data["params"]
            can_play_fhd = playlist_data["canPlayFHD"]
            separator = "&" if "?" in playlist_url else "?"
            m3u8_url = f"{playlist_url}{separator}expires={params.get('expires', '')}&token={params.get('token', '')}"
            if can_play_fhd:
                m3u8_url += "&h=1"
            print(f"Stream estratto per {movie_id}: {m3u8_url}")
            return m3u8_url
    except Exception as e:
        print(f"Errore Playwright per {movie_id}: {e}")
        logging.error(f"Errore Playwright per {movie_id}: {e}")
        return None

def create_m3u8_playlist():
    """Genera M3U8 con 50 film per categoria."""
    m3u8_content = ["#EXTM3U\n#EXTM3U generato da SimudFlix Python Script (Aggiornato 2025)\n"]

    for section, endpoint in ENDPOINTS.items():
        print(f"Fetching film per {section}...")
        movies = fetch_movies(endpoint)
        if not movies:
            print(f"Nessun film trovato per {section}")
            continue

        m3u8_content.append(f"\n# {section.capitalize()}\n")
        for movie in movies:
            title = movie.get("title", "Sconosciuto")
            movie_id = movie.get("id")
            details = fetch_movie_details(movie_id)
            genres = ",".join([g["name"] for g in details.get("genres", [])])
            release_year = details.get("release_date", "")[:4]
            poster = f"https://image.tmdb.org/t/p/w500{details.get('poster_path', '')}" if details.get("poster_path") else ""
            stream_url = get_stream_url(movie_id, is_movie=True) or f"https://example.com/placeholder/{movie_id}.m3u8"

            m3u8_content.append(
                f'#EXTINF:-1 tvg-id="{movie_id}" tvg-name="{title}" '
                f'tvg-year="{release_year}" tvg-genres="{genres}" '
                f'tvg-logo="{poster}",{title} ({release_year})\n'
                f"{stream_url}\n"
            )

    with open("simudflix_playlist.m3u8", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u8_content))
    print("M3U8 generato: simudflix_playlist.m3u8")

if __name__ == "__main__":
    print("Avvio generatore SimudFlix M3U8 (Versione Playwright)...")
    try:
        create_m3u8_playlist()
        print("Fatto! Controlla il file simudflix_playlist.m3u8 e testa con VLC.")
    except Exception as e:
        print(f"Errore generale: {e}")
        logging.error(f"Errore generale: {e}")
