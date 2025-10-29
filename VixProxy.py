#!/usr/bin/env python3
"""
TMDB M3U Playlist Generator - Versione corretta con tutte le categorie funzionanti
"""

import os
import requests
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

load_dotenv()

class TMDBM3UGenerator:
    def __init__(self):
        self.api_key = os.getenv("TMDB_API_KEY", "eff30813a2950a33e36b51ff09c71f97")
        self.base_url = "https://api.themoviedb.org/3"
        self.vixsrc_base = "https://vixsrc.to/movie"
        self.vixsrc_api = "https://vixsrc.to/api/list/movie/?lang=it"

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
            except Exception as e:
                print(f"Errore nel caricamento cache: {e}")
        return {}

    def _save_cache(self):
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
            print(f"Cache salvata ({len(self.cache)} film)")
        except Exception as e:
            print(f"Errore salvataggio cache: {e}")

    # -------------------------
    # vixsrc.to
    # -------------------------
    def _load_vixsrc_movies(self):
        try:
            print("Carico lista film da vixsrc.to...")
            res = requests.get(self.vixsrc_api, timeout=10)
            res.raise_for_status()
            data = res.json()
            ids = {str(i["tmdb_id"]) for i in data if i.get("tmdb_id")}
            print(f"Caricati {len(ids)} film disponibili da vixsrc.to")
            return ids
        except Exception as e:
            print(f"Attenzione: impossibile caricare lista vixsrc: {e}")
            return set()

    def _is_movie_available_on_vixsrc(self, tmdb_id):
        return str(tmdb_id) in self.vixsrc_movies

    # -------------------------
    # TMDB API
    # -------------------------
    def _fetch_movie_details(self, tmdb_id):
        url = f"{self.base_url}/movie/{tmdb_id}"
        params = {"api_key": self.api_key, "language": "it-IT"}
        try:
            r = requests.get(url, params=params, timeout=6)
            r.raise_for_status()
            m = r.json()
            return {
                "id": m["id"],
                "title": m["title"],
                "overview": m.get("overview", ""),
                "release_date": m.get("release_date", ""),
                "vote_average": m.get("vote_average", 0),
                "popularity": m.get("popularity", 0),
                "poster_path": m.get("poster_path", ""),
                "genres": [g.get("name", "").lower() for g in m.get("genres", [])],
            }
        except Exception as e:
            print(f"Errore nel fetch di {tmdb_id}: {e}")
            return None

    # -------------------------
    # Caricamento Film
    # -------------------------
    def _get_movies_from_vixsrc_list(self):
        movies = []
        total = len(self.vixsrc_movies)
        print(f"Recupero dettagli per {total} film (cache attiva)...")

        to_fetch = []
        for tid in self.vixsrc_movies:
            if tid in self.cache:
                movies.append(self.cache[tid])
            else:
                to_fetch.append(tid)

        print(f"{len(movies)} da cache, {len(to_fetch)} da scaricare")

        with ThreadPoolExecutor(max_workers=20) as ex:
            futures = {ex.submit(self._fetch_movie_details, tid): tid for tid in to_fetch}
            for i, f in enumerate(as_completed(futures), 1):
                m = f.result()
                if m:
                    movies.append(m)
                    self.cache[str(m["id"])] = m
                if i % 100 == 0:
                    print(f"  Progresso: {i}/{len(to_fetch)}")

        print(f"Totale film caricati: {len(movies)}")
        return movies

    # -------------------------
    # Filtri
    # -------------------------
    def _filter_cinepanettoni(self, movies):
        keywords = [
            "Natale", "Vacanze di Natale", "Boldi", "De Sica", "Salce",
            "Fantozzi", "Panettone", "Cortina", "Capodanno"
        ]
        return [
            m for m in movies
            if any(k.lower() in (m["title"] + " " + m.get("overview", "")).lower() for k in keywords)
        ]

    def _filter_category(self, movies, keywords=None, min_popularity=0, min_year=None):
        result = []
        for m in movies:
            if min_popularity and m.get("popularity", 0) < min_popularity:
                continue
            if min_year:
                year = m.get("release_date", "")[:4]
                if year and year.isdigit() and int(year) < min_year:
                    continue
            if keywords and not any(
                kw.lower() in " ".join(m.get("genres", [])).lower() for kw in keywords
            ):
                continue
            result.append(m)
        return result

    # -------------------------
    # Playlist
    # -------------------------
    def _write_movie_entry(self, f, movie, group):
        if not self._is_movie_available_on_vixsrc(movie["id"]):
            return
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

    def create_categorized_playlist(self):
        print("Creazione playlist M3U per categorie...")
        movies = self._get_movies_from_vixsrc_list()

        # --- categorie principali ---
        cinepanettoni = self._filter_cinepanettoni(movies)
        popolari = self._filter_category(movies, min_popularity=50, min_year=2020)
        animazione = self._filter_category(movies, keywords=["animation", "animazione"])
        azione = self._filter_category(movies, keywords=["action", "avventura", "adventure"])
        commedia = self._filter_category(movies, keywords=["comedy", "romance", "drama", "commedia", "dramma"])
        fantascienza = self._filter_category(movies, keywords=["science fiction", "fantascienza", "fantasy"])
        horror = self._filter_category(movies, keywords=["horror", "thriller"])

        sezioni = [
            ("Cinepanettoni 🎄", cinepanettoni),
            ("Nuovi / Popolari 🎬", popolari),
            ("Animazione 🧙‍♂️", animazione),
            ("Azione / Avventura 💥", azione),
            ("Commedia / Dramma 💘", commedia),
            ("Fantascienza / Fantasy 👽", fantascienza),
            ("Horror / Thriller 😱", horror),
            ("Tutti i Film 🎥", movies),
        ]

        path = os.path.join(self.output_dir, self.output_filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            f.write(f"#PLAYLIST:VixFilm Categorizzata ({len(movies)} Film)\n\n")

            for nome, lista in sezioni:
                if not lista:
                    continue
                f.write(f"# ===== {nome} =====\n")
                for m in lista:
                    self._write_movie_entry(f, m, nome)
                f.write("\n")

        self._save_cache()
        print(f"\n✅ Playlist generata con successo: {path}")

# -------------------------
# MAIN
# -------------------------
def main():
    try:
        g = TMDBM3UGenerator()
        print("TMDB M3U Playlist Generator con tutte le categorie funzionanti")
        print("=" * 40)
        g.create_categorized_playlist()
    except Exception as e:
        print(f"Errore: {e}")
        print("\nAssicurati di avere il TMDB_API_KEY impostato nel file .env")

if __name__ == "__main__":
    main()
