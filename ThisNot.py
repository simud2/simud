import cloudscraper
import re
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin
import base64
import json

# =============================
# CONFIGURAZIONE
# =============================
print("Inizializzazione del client cloudscraper...")
scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})

BASE_URL = "https://thisnot.business"
PASSWORD = "2025"

COMPETITIONS = {
    "SerieA": f"{BASE_URL}/serieA.php",
    "Bundesliga": f"{BASE_URL}/bundesliga.php",
    "LaLiga": f"{BASE_URL}/laliga.php",
    "PremierLeague": f"{BASE_URL}/premierleague.php",
    "ChampionsLeague": f"{BASE_URL}/championsleague.php",
}

# =============================
# FUNZIONI DI SUPPORTO
# =============================

def perform_login(url, pwd):
    print(f"\n🔑 Tentativo di login su {url}")
    try:
        response = scraper.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        form = soup.find('form')
        if form:
            action = form.get('action', '')
            action_url = urljoin(BASE_URL, action) if action else url
            inputs = {inp.get('name'): inp.get('value', '') for inp in form.find_all('input') if inp.get('name')}
        else:
            action_url = url
            inputs = {}
        inputs['password'] = pwd
        login_response = scraper.post(action_url, data=inputs, allow_redirects=True)
        login_response.raise_for_status()
        if "INSERIRE PASSWORD" not in login_response.text.upper():
            print("✅ Login riuscito")
            return True
        print("❌ Password non accettata")
        return False
    except Exception as e:
        print(f"Errore nel login: {e}")
        return False


def get_page_content(url):
    try:
        response = scraper.get(url, allow_redirects=True)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Errore nel caricamento di {url}: {e}")
        return None


def decode_token(token_raw):
    """Gestisce token base64 e JSON base64, correggendo il padding automaticamente."""
    try:
        # Corregge automaticamente il padding (aggiunge "=" fino a multiplo di 4)
        missing_padding = len(token_raw) % 4
        if missing_padding:
            token_raw += "=" * (4 - missing_padding)

        decoded_bytes = base64.b64decode(token_raw)
        decoded_str = decoded_bytes.decode('utf-8')

        if ':' in decoded_str:
            keyid, key = decoded_str.split(':', 1)
        elif decoded_str.strip().startswith('{'):
            data = json.loads(decoded_str)
            keyid, key = list(data.items())[0]
        else:
            print(f"⚠️ Formato token sconosciuto: {decoded_str}")
            return None, None

        return keyid.lower(), key.lower()
    except Exception as e:
        print(f"❌ Errore decodifica token '{token_raw}': {e}")
        return None, None


def process_competition(name, url):
    print(f"\n🏆 Elaborazione competizione: {name} ({url})")
    html_content = get_page_content(url)
    if not html_content:
        print(f"❌ Impossibile caricare la pagina di {name}")
        return

    soup = BeautifulSoup(html_content, 'html.parser')
    m3u8_content = "#EXTM3U\n"

    # Trova gruppi "data"
    data_sections = soup.find_all('div', class_='data')
    if not data_sections:
        print(f"Nessuna sezione 'data' trovata per {name}, cerco 'match-row' diretti...")
        match_rows = soup.find_all('div', class_='match-row')
        data_sections = [None] if match_rows else []
        if not match_rows:
            print(f"❌ Nessuna partita trovata per {name}")
            return

    total_matches = 0

    for data_section in data_sections:
        group_title = data_section.text.strip().upper() if data_section else name
        group_title = group_title.title()
        print(f"\n📅 Gruppo: {group_title}")

        match_rows = (
            data_section.find_next_siblings('div', class_='match-row')
            if data_section else soup.find_all('div', class_='match-row')
        )

        for i, match_row in enumerate(match_rows):
            try:
                home_div = match_row.find('div', class_='home team')
                away_div = match_row.find('div', class_='away team')
                if not home_div or not away_div:
                    continue

                home_team = home_div.find('span').text.strip() if home_div.find('span') else "Sconosciuta"
                away_team = away_div.find('span').text.strip() if away_div.find('span') else "Sconosciuta"
                channel_name = f"{home_team} VS {away_team}"
                print(f"\n⚽ {channel_name}")

                player_tag = match_row.find('a', href=True)
                if not player_tag:
                    continue
                player_url = urljoin(BASE_URL, player_tag['href'])
                player_content = get_page_content(player_url)
                if not player_content:
                    continue

                iframe_match = re.search(r'<iframe[^>]*src=["\']([^"\']+)["\']', player_content, re.IGNORECASE)
                if not iframe_match:
                    continue
                iframe_src = iframe_match.group(1)

                if iframe_src.startswith("chrome-extension://") and "#https://" in iframe_src:
                    iframe_src = iframe_src.split("#", 1)[1]

                if 'nochannel.php' in iframe_src:
                    print(f"⚠️ Nessun canale disponibile per {channel_name}")
                    continue

                # Estrae MPD e token
                mpd_url_match = re.search(r'https?://[^#"]+?\.mpd', iframe_src)
                token_match = re.search(r'ck=([A-Za-z0-9+/=_-]+)', iframe_src)
                if not mpd_url_match or not token_match:
                    print(f"❌ MPD o token mancanti per {channel_name}")
                    continue

                mpd_url = mpd_url_match.group(0)
                token_raw = token_match.group(1)
                keyid, key = decode_token(token_raw)
                if not keyid or not key:
                    continue

                m3u8_content += f'#EXTINF:-1 tvg-id="dazn" tvg-logo="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTOyE-K-43FZ_16IFb9aUbFKSHYpAVmEC-jhw&s" group-title="{group_title}",{channel_name}\n'
                m3u8_content += '#KODIPROP:inputstream.adaptive.license_type=clearkey\n'
                m3u8_content += f'#KODIPROP:inputstream.adaptive.license_key={keyid}:{key}\n'
                m3u8_content += f'{mpd_url}\n\n'
                total_matches += 1

            except Exception as e:
                print(f"Errore partita {i+1}: {e}")
                continue

    # Salva M3U8 nella stessa cartella
    if total_matches > 0:
        file_path = os.path.join(os.getcwd(), f"{name}_ThisNot.m3u8")
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(m3u8_content)
            print(f"\n✅ File M3U8 salvato: {file_path} ({total_matches} partite)")
        except Exception as e:
            print(f"Errore salvataggio file {name}: {e}")
    else:
        print(f"⚠️ Nessuna partita valida trovata per {name}")


# =============================
# ESECUZIONE PRINCIPALE
# =============================

if not perform_login(f"{BASE_URL}/serieA.php", PASSWORD):
    print("FATAL: Login fallito. Interrompo.")
    exit()

for comp_name, comp_url in COMPETITIONS.items():
    process_competition(comp_name, comp_url)

print("\n🎉 Tutte le competizioni elaborate correttamente!")
