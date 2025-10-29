#!/usr/bin/env python3
"""
TMDB M3U Playlist Generator - versione completa con categorie reali e proxy Stremio
"""

import os
import requests
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv()


class TMDBM3UGenerator:
    def __init__(self):
        self.api_key = os.getenv("TMDB_API_KEY", "eff30813a2950a33e36b51ff09c71f97")
        self.base_url = "https://api.themoviedb.org/3"
        self.vixsrc_base = "https://vixsrc.to/movie"
        self.vixsrc_api = "https://vixsrc.to/api/list/movie/?lang=it"
        self.proxy_prefix = "https://proxy.stremio.dpdns.org/manifest.m3u8?url="

        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.output_dir = script_dir
        self.output_filename = "VixFilm.m3u8"
        self.cache_file = os.path.join(script_dir, "film_cache.json")

        self.cache = self._load_cache()
        self.vixsrc_movies = self._load_vixsrc_movies()

    # -------------------------
    # Cache
    # -------------------------
    def _load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_cache(self):
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
            print(f"Cache salvata ({len(self.cache)} film)")
        except Exception as e:
            print("Errore salvataggio cache:", e)

    # -------------------------
    # vixsrc.to
    # -------------------------
    def _load_vixsrc_movies(self):
        try:
            print("Carico lista film da vixsrc.to...")
            r = requests.get(self.vixsrc_api, timeout=10)
            r.raise_for_status()
            data = r.json()
            return {str(i["tmdb_id"]) for i in data if i.get("tmdb_id")}
        except Exception as e:
            print("Errore caricamento lista:", e)
            return set()

    def _is_on_vixsrc(self, tmdb_id):
        return str(tmdb_id) in self.vixsrc_movies

    # -------------------------
    # TMDB API helpers
    # -------------------------
    def _fetch_tmdb_json(self, endpoint, params=None):
        params = params or {}
        params["api_key"] = self.api_key
        params["language"] = "it-IT"
        try:
            r = requests.get(f"{self.base_url}/{endpoint}", params=params, timeout=6)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"Errore fetch {endpoint}: {e}")
            return {}

    def get_genres(self):
        data = self._fetch_tmdb_json("genre/movie/list")
        return {g["id"]: g["name"] for g in data.get("genres", [])}

    def get_popular_ids(self, pages=3):
        ids = set()
        for p in range(1, pages + 1):
            data = self._fetch_tmdb_json("movie/popular", {"page": p})
            ids.update(str(m["id"]) for m in data.get("results", []))
        return ids

    def get_now_playing_ids(self, pages=2):
        ids = set()
        for p in range(1, pages + 1):
            data = self._fetch_tmdb_json("movie/now_playing", {"page": p})
            ids.update(str(m["id"]) for m in data.get("results", []))
        return ids

    def get_top_rated_ids(self, pages=2):
        ids = set()
        for p in range(1, pages + 1):
            data = self._fetch_tmdb_json("movie/top_rated", {"page": p})
            ids.update(str(m["id"]) for m in data.get("results", []))
        return ids

    def _fetch_movie_details(self, tmdb_id):
        if str(tmdb_id) in self.cache:
            return self.cache[str(tmdb_id)]
        data = self._fetch_tmdb_json(f"movie/{tmdb_id}")
        if not data or "id" not in data:
            return None
        m = {
            "id": data["id"],
            "title": data["title"],
            "release_date": data.get("release_date", ""),
            "vote_average": data.get("vote_average", 0),
            "poster_path": data.get("poster_path", ""),
            "genre_ids": [g["id"] for g in data.get("genres", [])],
        }
        self.cache[str(m["id"])] = m
        return m

    # -------------------------
    # Data loading
    # -------------------------
    def _get_vixsrc_movies(self):
        print(f"Scarico dettagli per {len(self.vixsrc_movies)} film...")
        movies = []
        to_fetch = [tid for tid in self.vixsrc_movies if tid not in self.cache]

        with ThreadPoolExecutor(max_workers=20) as ex:
            futures = {ex.submit(self._fetch_movie_details, tid): tid for tid in to_fetch}
            for i, f in enumerate(as_completed(futures), 1):
                m = f.result()
                if m:
                    movies.append(m)
                if i % 100 == 0:
                    print(f"   Progresso: {i}/{len(to_fetch)}")

        movies.extend(self.cache[tid] for tid in self.vixsrc_movies if tid in self.cache)
        print(f"Totale film caricati: {len(movies)}")
        return movies

    # -------------------------
    # Playlist writing
    # -------------------------
    def _write_entry(self, f, m, group):
        if not self._is_on_vixsrc(m["id"]):
            return
        title = m["title"]
        year = m.get("release_date", "")[:4]
        logo = f"https://image.tmdb.org/t/p/w500{m['poster_path']}" if m.get("poster_path") else ""
        base_url = f"{self.vixsrc_base}/{m['id']}/?lang=it"
        # 🔹 Aggiungiamo il proxy davanti
        proxy_url = f"{self.proxy_prefix}{base_url}"
        f.write(f'#EXTINF:-1 tvg-logo="{logo}" group-title="Film - {group}",{title} ({year})\n')
        f.write(f"{proxy_url}\n\n")

    # -------------------------
    # Main creation
    # -------------------------
    def create_playlist(self):
        print("Creazione playlist...")
        genres = self.get_genres()
        movies = self._get_vixsrc_movies()

        # categorie da TMDB reali
        pop_ids = self.get_popular_ids()
        now_ids = self.get_now_playing_ids()
        top_ids = self.get_top_rated_ids()

        cinepanettoni = [
            m for m in movies
            if any(k.lower() in m["title"].lower() for k in ["Natale", "Boldi", "De Sica", "Vacanze"])
        ]
        popolari = [m for m in movies if str(m["id"]) in pop_ids]
        cinema = [m for m in movies if str(m["id"]) in now_ids]
        top = [m for m in movies if str(m["id"]) in top_ids]

        # Categorie per genere
        genre_map = {g: [] for g in genres.values()}
        for m in movies:
            for gid in m.get("genre_ids", []):
                name = genres.get(gid)
                if name:
                    genre_map[name].append(m)

        # Scrittura file
        path = os.path.join(self.output_dir, self.output_filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            f.write(f"#PLAYLIST:VixFilm ({len(movies)} Film)\n\n")

            def section(name, lst):
                if lst:
                    print(f"Aggiungo sezione: {name} ({len(lst)})")
                    f.write(f"# ===== {name} =====\n")
                    for m in lst:
                        self._write_entry(f, m, name)
                    f.write("\n")

            section("Cinepanettoni 🎄", cinepanettoni)
            section("Al Cinema 🎬", cinema)
            section("Popolari ⭐", popolari)
            section("Più Votati 🏆", top)

            for gname, glist in genre_map.items():
                section(gname, sorted(glist, key=lambda x: x.get("release_date", ""), reverse=True))

            section("Tutti i Film 🎥", movies)

        self._save_cache()
        print(f"\n✅ Playlist generata con successo: {path}")


def main():
    try:
        g = TMDBM3UGenerator()
        print("TMDB M3U Playlist Generator con proxy Stremio e categorie reali")
        print("=" * 40)
        g.create_playlist()
    except Exception as e:
        print("Errore:", e)


if __name__ == "__main__":
    main()
