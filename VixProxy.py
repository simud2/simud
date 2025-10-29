#!/usr/bin/env python3
"""
TMDB M3U Playlist Generator
Fetches movies from TMDB API and creates an M3U playlist with vixsrc.to links
"""

import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

# Load environment variables
load_dotenv()

class TMDBM3UGenerator:
    def __init__(self):
        self.api_key = "eff30813a2950a33e36b51ff09c71f97"
        self.base_url = "https://api.themoviedb.org/3"
        self.vixsrc_base = "https://vixsrc.to/movie"
        self.vixsrc_api = "https://vixsrc.to/api/list/movie/?lang=it"

        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.output_dir = os.path.dirname(script_dir)
        self.output_filename = "VixFlim.m3u8"
        self.cache_file = os.path.join(script_dir, "film_cache.json")

        self.cache = self._load_cache()
        self.vixsrc_movies = self._load_vixsrc_movies()

    # -------------------------
    # Cache Management
    # -------------------------
    def _load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading cache: {e}")
        return {}

    def _save_cache(self):
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
            print(f"Cache saved ({len(self.cache)} movies)")
        except Exception as e:
            print(f"Error saving cache: {e}")

    # -------------------------
    # Load Vixsrc list
    # -------------------------
    def _load_vixsrc_movies(self):
        try:
            print("Loading vixsrc.to movie list...")
            res = requests.get(self.vixsrc_api, timeout=10)
            res.raise_for_status()
            data = res.json()
            ids = {str(i["tmdb_id"]) for i in data if i.get("tmdb_id")}
            print(f"Loaded {len(ids)} available movies from vixsrc.to")
            return ids
        except Exception as e:
            print(f"Warning: Could not load vixsrc list: {e}")
            return set()

    def _is_movie_available_on_vixsrc(self, tmdb_id):
        return str(tmdb_id) in self.vixsrc_movies

    # -------------------------
    # TMDB API
    # -------------------------
    def get_movie_genres(self):
        url = f"{self.base_url}/genre/movie/list"
        params = {"api_key": self.api_key, "language": "it-IT"}
        r = requests.get(url, params=params)
        r.raise_for_status()
        return {g["id"]: g["name"] for g in r.json()["genres"]}

    def _fetch_movie_details(self, tmdb_id):
        url = f"{self.base_url}/movie/{tmdb_id}"
        params = {"api_key": self.api_key, "language": "it-IT"}
        try:
            r = requests.get(url, params=params, timeout=5)
            r.raise_for_status()
            m = r.json()
            return {
                "id": m["id"],
                "title": m["title"],
                "release_date": m.get("release_date", ""),
                "vote_average": m.get("vote_average", 0),
                "poster_path": m.get("poster_path", ""),
                "genre_ids": [g["id"] for g in m.get("genres", [])],
            }
        except Exception as e:
            print(f"Error fetching {tmdb_id}: {e}")
            return None

    # -------------------------
    # Load Movies
    # -------------------------
    def _get_movies_from_vixsrc_list(self):
        """Fetch movie details for all available Vixsrc movies, using cache"""
        movies = []
        total = len(self.vixsrc_movies)
        print(f"Fetching details for {total} movies (cache supported)...")

        to_fetch = []
        for tid in self.vixsrc_movies:
            if tid in self.cache:
                movies.append(self.cache[tid])
            else:
                to_fetch.append(tid)

        print(f"{len(movies)} from cache, {len(to_fetch)} to fetch")

        with ThreadPoolExecutor(max_workers=20) as ex:
            futures = {ex.submit(self._fetch_movie_details, tid): tid for tid in to_fetch}
            for i, f in enumerate(as_completed(futures), 1):
                m = f.result()
                if m:
                    movies.append(m)
                    self.cache[str(m["id"])] = m
                if i % 100 == 0:
                    print(f"  Progress: {i}/{len(to_fetch)}")

        print(f"Loaded {len(movies)} movies total")
        return movies

    # -------------------------
    # Playlist Creation
    # -------------------------
    def _write_movie_entry(self, f, movie, genres, group):
        if not self._is_movie_available_on_vixsrc(movie["id"]):
            return False
        title = movie["title"]
        year = movie.get("release_date", "")[:4]
        logo = (
            f"https://image.tmdb.org/t/p/w500{movie['poster_path']}"
            if movie.get("poster_path")
            else ""
        )
        url = f"{self.vixsrc_base}/{movie['id']}/?lang=it"
        f.write(
            f'#EXTINF:-1 tvg-logo="{logo}" group-title="Film - {group}",{title} ({year})\n'
        )
        f.write(f"https://proxy.stremio.dpdns.org/manifest.m3u8?url={url}\n\n")
        return True

    def _organize_and_write_movies(self, f, movies, genres):
        f.write("# Tutti i Film\n")
        for m in movies:
            self._write_movie_entry(f, m, genres, "Tutti")

    def create_complete_playlist(self):
        print("Creating complete M3U playlist from vixsrc.to movies...")
        genres = self.get_movie_genres()
        movies = self._get_movies_from_vixsrc_list()
        path = os.path.join(self.output_dir, self.output_filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            f.write(f"#PLAYLIST:VixFlim ({len(movies)} Film)\n\n")
            self._organize_and_write_movies(f, movies, genres)
        self._save_cache()
        print(f"\n✅ Playlist generated successfully: {path}")

# -------------------------
# MAIN
# -------------------------
def main():
    try:
        g = TMDBM3UGenerator()
        print("TMDB M3U Playlist Generator")
        print("=" * 40)
        g.create_complete_playlist()
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure to set your TMDB_API_KEY environment variable:")
        print("1. Get your API key from https://www.themoviedb.org/settings/api")
        print("2. Create a .env file with: TMDB_API_KEY=your_api_key_here")

if __name__ == "__main__":
    main()
