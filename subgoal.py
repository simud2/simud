import cloudscraper
from bs4 import BeautifulSoup
import re
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
from urllib.parse import urlparse

# URL modificabile
base_url = "https://sub7goal.site/"

# Nome del file M3U8 nella directory corrente
output_file = "subgoal.m3u8"

# User-Agent predefinito
user_agent = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"

# URL dell'immagine per tvg-logo
tvg_logo = "https://resource-m.calcionapoli24.it/www/thumbs/1200x/1671957248_90.jpg"

# Inizializza cloudscraper
scraper = cloudscraper.create_scraper()

def get_event_links(url):
    try:
        # Ottieni il codice sorgente della pagina
        response = scraper.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Trova tutti i link che contengono "anonpaste.pw"
        links = soup.find_all('a', href=re.compile(r'https://anonpaste\.pw'))
        return links
    except Exception as e:
        print(f"Errore durante il recupero della pagina {url}: {e}")
        return []

def get_stream_links(event_url):
    try:
        # Configura Selenium con Chrome
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")  # Esegui in modalità headless
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        
        # Carica la pagina
        driver.get(event_url)
        time.sleep(3)  # Attendi il caricamento dinamico

        # Ottieni il contenuto della pagina
        page_source = driver.page_source
        driver.quit()

        # Analizza il contenuto con BeautifulSoup
        soup = BeautifulSoup(page_source, 'html.parser')
        text_content = soup.get_text()
        lines = text_content.split('\n')

        stream_data = []
        current_title = ""
        current_category = ""

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Cerca la categoria (es. "🇪🇺 Europa - UEFA Champions League" o "🇮🇹 Italia - Serie C")
            if re.match(r'🇪🇺|🇮🇹', line) and not re.search(r'\d{2}:\d{2}', line):
                current_category = line
                continue

            # Cerca il titolo dell'evento (es. "18:45 Diretta Goal" o "18:45 Olympiakos Piraeus vs Paphos")
            if re.match(r'\d{2}:\d{2}', line):
                current_title = f"{current_category} - {line}"
                continue

            # Cerca i link con (🇮🇹)
            if "(🇮🇹)" in line:
                match = re.search(r'(https?://[^\s]+)\s*\(🇮🇹\)', line)
                if match and current_title:
                    stream_url = match.group(1)
                    stream_data.append({"title": current_title, "url": stream_url})

        return stream_data
    except Exception as e:
        print(f"Errore durante il recupero della pagina {event_url}: {e}")
        return []

def save_m3u8(stream_data):
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            # Intestazione del file M3U8
            f.write('#EXTM3U\n')
            # Aggiungi ogni flusso al file con opzioni VLC e tvg-logo
            for stream in stream_data:
                # Estrai il dominio dall'URL del flusso
                parsed_url = urlparse(stream["url"])
                domain = f"{parsed_url.scheme}://{parsed_url.netloc}/"
                
                # Scrivi le opzioni VLC e tvg-logo
                f.write(f'#EXTINF:-1 tvg-logo="{tvg_logo}",{stream["title"]}\n')
                f.write(f'#EXTVLCOPT:http-referrer={domain}\n')
                f.write(f'#EXTVLCOPT:http-origin={domain}\n')
                f.write(f'#EXTVLCOPT:http-user-agent={user_agent}\n')
                f.write(f'{stream["url"]}\n')
        print(f"File M3U8 salvato con successo come: {output_file}")
    except Exception as e:
        print(f"Errore durante il salvataggio del file M3U8: {e}")

def main():
    # Ottieni i link agli eventi dalla pagina principale
    event_links = get_event_links(base_url)
    if not event_links:
        print("Nessun link agli eventi trovato.")
        return

    all_streams = []
    # Per ogni link agli eventi, estrai i flussi
    for link in event_links:
        event_url = link['href']
        print(f"Elaborazione link evento: {event_url}")
        stream_data = get_stream_links(event_url)
        all_streams.extend(stream_data)

    if all_streams:
        # Salva i flussi in un file M3U8
        save_m3u8(all_streams)
    else:
        print("Nessun flusso con (🇮🇹) trovato.")

if __name__ == "__main__":
    main()
