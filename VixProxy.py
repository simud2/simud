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
import time
import json
import hashlib

# Load environment variables
load_dotenv()

class TMDBM3UGenerator:
    def __init__(self):
        self.api_key = "eff30813a2950a33e36b51ff09c71f97"
        self.base_url = "https://api.themoviedb.org/3"
        self.vixsrc_base = "https://vixsrc.to/movie"
        self.vixsrc_api = "https://vixsrc.to/api/list/movie/?lang=it"

        # Definisce il percorso di base per i file di output (la cartella genitore dello script)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.output_dir = os.path.dirname(script_dir)
        self.output_filename = "VixFlim.m3u8"  # <--- Nome file aggiornato
        self.cache_file = os.path.join(script_dir, "film_cache.json")
        self.cache = self._load_cache()
        self.vixsrc_movies = self._load_vixsrc_movies()
        
        if not self.api_key:
            raise ValueError("TMDB_API_KEY environment variable is required")
    
    def _load_vixsrc_movies(self):
        """Load available movies from vixsrc.to API"""
        try:
            print("Loading vixsrc.to movie list...")
            response = requests.get(self.vixsrc_api, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Extract tmdb_ids from the response
            vixsrc_ids = set()
            for item in data:
                if item.get('tmdb_id') and item['tmdb_id'] is not None:
                    vixsrc_ids.add(str(item['tmdb_id']))
            
            print(f"Loaded {len(vixsrc_ids)} available movies from vixsrc.to")
            return vixsrc_ids
        except Exception as e:
            print(f"Warning: Could not load vixsrc.to movie list: {e}")
            print("Continuing without vixsrc.to verification...")
            return set()
    
    def _is_movie_available_on_vixsrc(self, tmdb_id):
        """Check if movie is available on vixsrc.to"""
        return str(tmdb_id) in self.vixsrc_movies
    
    def _load_cache(self):
        """Load existing cache from file"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                print(f"Loaded cache with {len(cache)} movies")
                return cache
            except Exception as e:
                print(f"Error loading cache: {e}")
        return {}
    
    def _save_cache(self):
        """Save cache to file"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
            print(f"Cache saved with {len(self.cache)} movies")
        except Exception as e:
            print(f"Error saving cache: {e}")
    
    def _get_cache_key(self, movie):
        """Generate cache key for a movie"""
        return str(movie['id'])
    
    def _is_movie_cached(self, movie):
        """Check if movie is already in cache"""
        cache_key = self._get_cache_key(movie)
        return cache_key in self.cache
    
    def _add_to_cache(self, movie):
        """Add movie to cache"""
        cache_key = self._get_cache_key(movie)
        self.cache[cache_key] = {
            'id': movie['id'],
            'title': movie['title'],
            'release_date': movie.get('release_date', ''),
            'vote_average': movie.get('vote_average', 0),
            'poster_path': movie.get('poster_path', ''),
            'genre_ids': movie.get('genre_ids', []),
            'cached_at': datetime.now().isoformat()
        }
    
    def get_popular_movies(self, page=1, language='it-IT'):
        """Fetch popular movies from TMDB"""
        url = f"{self.base_url}/movie/popular"
        params = {
            'api_key': self.api_key,
            'page': page,
            'language': language
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def get_top_rated_movies(self, page=1, language='it-IT'):
        """Fetch top rated movies from TMDB"""
        url = f"{self.base_url}/movie/top_rated"
        params = {
            'api_key': self.api_key,
            'page': page,
            'language': language
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def get_all_movies(self, page=1, language='it-IT'):
        """Fetch all movies from TMDB (discover endpoint)"""
        url = f"{self.base_url}/discover/movie"
        params = {
            'api_key': self.api_key,
            'page': page,
            'language': language,
            'sort_by': 'popularity.desc',
            'include_adult': False,
            'include_video': False
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def get_movie_genres(self):
        """Fetch movie genres from TMDB"""
        url = f"{self.base_url}/genre/movie/list"
        params = {
            'api_key': self.api_key,
            'language': 'it-IT'
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        return {genre['id']: genre['name'] for genre in response.json()['genres']}
    
    def get_latest_movies(self, page=1, language='it-IT'):
        """Fetch latest movies from TMDB"""
        url = f"{self.base_url}/movie/now_playing"
        params = {
            'api_key': self.api_key,
            'page': page,
            'language': language
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def generate_m3u_playlist(self, movies_data, output_file="tmdb_movies.m3u"):
        """Generate M3U playlist from movies data"""
        genres = self.get_movie_genres()
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n")
            f.write(f"# Generated by TMDB M3U Generator on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Total movies: {len(movies_data)}\n\n")
            for movie in movies_data:
                tmdb_id = movie['id']
                title = movie['title']
                year = movie.get('release_date', '')[:4] if movie.get('release_date') else ''
                rating = movie.get('vote_average', 0)
                genre_names = []
                if movie.get('genre_ids') and movie['genre_ids']:
                    for genre_id in movie['genre_ids']:
                        genre_name = genres.get(genre_id, "")
                        if genre_name:
                            genre_names.append(genre_name)
                primary_genre = genre_names[0] if genre_names else "Film"
                poster_path = movie.get('poster_path', '')
                tvg_logo = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ""
                movie_url = f"{self.vixsrc_base}/{tmdb_id}/?lang=it"
                display_title = f"{title} ({year})"
                f.write(f'#EXTINF:-1 type="movie" tvg-logo="{tvg_logo}" group-title="Film - {primary_genre}",{display_title}\n')
                f.write(f"{movie_url}\n")
        print(f"Playlist generated successfully: {output_file}")
    
    def create_complete_playlist(self):
        """Create one complete M3U file with all categories and genres"""
        print("Creating complete M3U playlist from vixsrc.to movies...")
        genres = self.get_movie_genres()
        print(f"\nFetching movie details for {len(self.vixsrc_movies)} available movies...")
        movies_data = self._get_movies_from_vixsrc_list()
        total_movies = len(movies_data)
        
        output_path = os.path.join(self.output_dir, self.output_filename)  # <--- Nome aggiornato
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n")
            f.write(f"#PLAYLIST:Film VixSrc ({total_movies} Film)\n\n")
            self._organize_and_write_movies(f, movies_data, genres)
        self._save_cache()
        print(f"\nComplete playlist generated successfully: {output_path}")

    # (tutto il resto del codice resta invariato, inclusi i metodi _get_movies_from_vixsrc_list, _fetch_movie_details, ecc.)

def main():
    """Main function to run the generator"""
    try:
        generator = TMDBM3UGenerator()
        print("TMDB M3U Playlist Generator")
        print("=" * 40)
        generator.create_complete_playlist()
        print("\nAll playlists generated successfully!")
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure to set your TMDB_API_KEY environment variable:")
        print("1. Get your API key from https://www.themoviedb.org/settings/api")
        print("2. Create a .env file with: TMDB_API_KEY=your_api_key_here")

if __name__ == "__main__":
    main()
