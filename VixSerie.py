#!/usr/bin/env python3
"""
VixSerie M3U Playlist Generator
Crea una playlist M3U8 con le serie TV di vixsrc.to (con proxy Stremio e categorie TMDB)
"""

import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

load_dotenv()


class TVM3UGenerator:
    def __init__(self):
        self.api_key = "eff30813a2950a33e36b51ff09c71f97"
        self.base_url = "https://api.themoviedb.org/3"
        self.vixsrc_base = "https://vixsrc.to/tv"
        self.vixsrc_api = "https://vixsrc.to/api/list/episode/?lang=it"
        self.proxy_prefix = "https://proxy.stremio.dpdns.org/manifest.m3u8?url="

        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.output_dir = script_dir
        self.output_filename = "VixSerie.m3u8"
        self.cache_file = os.path.join(script_dir, "serie_cache.json")

        self.cache = self._load_cache()
        self.episodes_data = self._load_vixsrc_episodes()

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
            print(f"Cache salvata ({len(self.cache)} serie)")
        except Exception as e:
            print(f"Errore salvataggio cache: {e}")

    # -------------------------
    # vixsrc.to
    # -------------------------
    def _load_vixsrc_episodes(self):
        try:
            print("Caricamento episodi da vixsrc.to...")
            r = requests.get(self.vixsrc_api, timeout=10)
            r.raise_for_status()
            data = r.json()
            print(f"Caricati {len(data)} episodi totali.")
            return data
        except Exception as e:
            print(f"Errore caricamento lista vixsrc: {e}")
            return []

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
            print(f"Errore TMDB {endpoint}: {e}")
            return {}

    def get_tv_genres(self):
        data = self._fetch_tmdb_json("genre/tv/list")
        return {g["id"]: g["name"] for g in data.get("genres", [])}

    def get_popular_ids(self, pages=3):
        ids = set()
        for p in range(1, pages + 1):
            data = self._fetch_tmdb_json("tv/popular", {"page": p})
            ids.update(str(s["id"]) for s in data.get("results", []))
        return ids

    def get_on_air_ids(self, pages=2):
        ids = set()
        for p in range(1, pages + 1):
            data = self._fetch_tmdb_json("tv/on_the_air", {"page": p})
            ids.update(str(s["id"]) for s in data.get("results", []))
        return ids

    def get_top_rated_ids(self, pages=2):
        ids = set()
        for p in range(1, pages + 1):
            data = self._fetch_tmdb_json("tv/top_rated", {"page": p})
            ids.update(str(s["id"]) for s in data.get("results", []))
        return ids

    def _fetch_series_details(self, tmdb_id):
        if str(tmdb_id) in self.cache:
            return self.cache[str(tmdb_id)]
        data = self._fetch_tmdb_json(f"tv/{tmdb_id}")
        if not data or "id" not in data:
            return None
        s = {
            "id": data["id"],
            "name": data["name"],
            "first_air_date": data.get("first_air_date", ""),
            "vote_average": data.get("vote_average", 0),
            "poster_path": data.get("poster_path", ""),
            "genre_ids": [g["id"] for g in data.get("genres", [])],
        }
        self.cache[str(s["id"])] = s
        return s

    # -------------------------
    # Organizza episodi
    # -------------------------
    def _organize_episodes_by_series(self):
        series_episodes = defaultdict(lambda: defaultdict(list))
        for ep in self.episodes_data:
            tid = ep.get("tmdb_id")
            if not tid:
                continue
            s = ep.get("s")
            e = ep.get("e")
            if s and e:
                series_episodes[tid][s].append(e)
        for sid in series_episodes:
            for s in series_episodes[sid]:
                series_episodes[sid][s].sort()
        return series_episodes

    def _get_series_from_vixsrc_list(self, ids):
        series_data = []
        to_fetch = []
        for tid in ids:
            if str(tid) in self.cache:
                series_data.append(self.cache[str(tid)])
            else:
                to_fetch.append(tid)

        print(f"{len(series_data)} da cache, {len(to_fetch)} da scaricare...")

        with ThreadPoolExecutor(max_workers=20) as ex:
            futures = {ex.submit(self._fetch_series_details, tid): tid for tid in to_fetch}
            for f in as_completed(futures):
                s = f.result()
                if s:
                    self.cache[str(s["id"])] = s
                    series_data.append(s)
        return series_data

    # -------------------------
    # Scrittura playlist
    # -------------------------
    def create_playlist(self):
        print("Creazione playlist completa Serie TV...")
        genres = self.get_tv_genres()
        series_episodes = self._organize_episodes_by_series()
        ids = list(series_episodes.keys())
        print(f"Trovate {len(ids)} serie con episodi.")
        series_data = self._get_series_from_vixsrc_list(ids)

        # Otteniamo categorie reali da TMDB
        popular_ids = self.get_popular_ids()
        on_air_ids = self.get_on_air_ids()
        top_ids = self.get_top_rated_ids()

        # Dividiamo per categorie
        on_air = [s for s in series_data if str(s["id"]) in on_air_ids]
        popular = [s for s in series_data if str(s["id"]) in popular_ids]
        top_rated = [s for s in series_data if str(s["id"]) in top_ids]

        # Mappa generi
        genre_map = {g: [] for g in genres.values()}
        for s in series_data:
            for gid in s.get("genre_ids", []):
                name = genres.get(gid)
                if name:
                    genre_map[name].append(s)

        path = os.path.join(self.output_dir, self.output_filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            f.write(f"#PLAYLIST:VixSerie ({len(series_data)} Serie)\n\n")

            def section(title, items):
                if not items:
                    return
                print(f"Aggiungo sezione: {title} ({len(items)})")
                f.write(f"# ===== {title} =====\n")
                for s in items:
                    self._write_series_entries(f, s, series_episodes, title)
                f.write("\n")

            section("📺 In Onda Ora", on_air)
            section("⭐ Popolari", popular)
            section("🏆 Più Votate", top_rated)

            for gname, glist in genre_map.items():
                section(gname, sorted(glist, key=lambda x: x.get("first_air_date", ""), reverse=True))

            section("🎥 Tutte le Serie", series_data)

        self._save_cache()
        print(f"\n✅ Playlist generata con successo: {path}")

    def _write_series_entries(self, f, series, series_episodes, group):
        tid = series["id"]
        if tid not in series_episodes:
            return
        name = series["name"]
        year = series.get("first_air_date", "")[:4]
        logo = f"https://image.tmdb.org/t/p/w500{series['poster_path']}" if series.get("poster_path") else ""

        for season, eps in sorted(series_episodes[tid].items()):
            for e in eps:
                base_url = f"{self.vixsrc_base}/{tid}/{season}/{e}?lang=it"
                # 🔹 Proxy Stremio davanti
                proxy_url = f"{self.proxy_prefix}{base_url}"
                display = f"{name} S{season:02d}E{e:02d} ({year})"
                f.write(f'#EXTINF:-1 tvg-logo="{logo}" group-title="SerieTV - {group}",{display}\n')
                f.write(f"{proxy_url}\n\n")


def main():
    try:
        g = TVM3UGenerator()
        print("== TMDB Serie M3U Playlist Generator ==")
        print("=" * 40)
        g.create_playlist()
    except Exception as e:
        print("Errore:", e)


if __name__ == "__main__":
    main()
