import cloudscraper
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import os

# Configurazioni
BASE_URL = "https://ava.karmakurama.com/schedule.php"
M3U_HEADER = '#EXTM3U\n'
USER_AGENT = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
REFERRER = "https://ava.karmakurama.com/"
ORIGIN = "https://ava.karmakurama.com/"
LOGO_URL = "https://img.freepik.com/vettori-premium/vettore-del-logo-del-marchio-sportivo-9_666870-2780.jpg?semt=ais_incoming&w=740&q=80"

def scrape_page():
    scraper = cloudscraper.create_scraper()
    response = scraper.get(BASE_URL)
    if response.status_code != 200:
        print(f"Errore: Impossibile accedere alla pagina (codice {response.status_code})")
        return None
    return response.text

def parse_events(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    events_by_sport = {}
    italian_channels = []
    calcio_italy_channels = []

    date_accordions = soup.find_all('div', class_='accordion-collapse', id=re.compile('dt-\d{4}-\d{2}-\d{2}'))
    
    for date_accordion in date_accordions:
        sport_accordions = date_accordion.find_all('div', class_='accordion-item')
        
        for sport_accordion in sport_accordions:
            sport_name = sport_accordion.find('button', class_='accordion-button').text.strip()
            if sport_name not in events_by_sport:
                events_by_sport[sport_name] = []
            
            event_items = sport_accordion.find_all('div', class_='accordion-item acc-event-data')
            
            for event_item in event_items:
                event_button = event_item.find('button', class_='accordion-button')
                event_name = event_button.text.strip()
                # Rimuovi l'orario (es. "16:45:00 - ") dall'inizio del titolo
                cleaned_event_name = re.sub(r'^\d{2}:\d{2}:\d{2}\s*-\s*', '', event_name)
                
                channel_links = event_item.find_all('a', class_='btn btn-outline-primary')
                for channel in channel_links:
                    channel_name = channel.text.strip()
                    channel_url = urljoin(BASE_URL, channel['href'])
                    
                    # Filtro per canali italiani: solo parole standalone "IT", "Italy", "Italia", "it"
                    if re.search(r'\b(?:IT|Italy|Italia|it)\b', channel_name, re.IGNORECASE):
                        if sport_name == "Soccer":
                            # Aggiungi al gruppo Calcio Italy se è un evento di Soccer
                            calcio_italy_channels.append({
                                'event': f"{cleaned_event_name} ({channel_name})",
                                'url': channel_url,
                                'sport': sport_name
                            })
                        else:
                            # Aggiungi al gruppo Sport Italy per altri sport
                            italian_channels.append({
                                'event': f"{cleaned_event_name} ({channel_name})",
                                'url': channel_url,
                                'sport': sport_name
                            })
                    else:
                        # Aggiungi al gruppo dello sport corrispondente
                        events_by_sport[sport_name].append({
                            'event': f"{cleaned_event_name} ({channel_name})",
                            'url': channel_url
                        })
    
    return events_by_sport, italian_channels, calcio_italy_channels

def generate_m3u(events_by_sport, italian_channels, calcio_italy_channels):
    m3u_content = M3U_HEADER
    
    # Aggiungi i canali di Calcio Italy
    if calcio_italy_channels:
        for channel in calcio_italy_channels:
            m3u_content += f'#EXTINF:-1 tvg-logo="{LOGO_URL}" group-title="Calcio Italy",{channel["event"]}\n'
            m3u_content += f'#EXTVLCOPT:http-referrer={REFERRER}\n'
            m3u_content += f'#EXTVLCOPT:http-origin={ORIGIN}\n'
            m3u_content += f'#EXTVLCOPT:http-user-agent={USER_AGENT}\n'
            m3u_content += f'{channel["url"]}\n'
    
    # Aggiungi i canali italiani (Sport Italy)
    if italian_channels:
        for channel in italian_channels:
            m3u_content += f'#EXTINF:-1 tvg-logo="{LOGO_URL}" group-title="Sport Italy",{channel["event"]}\n'
            m3u_content += f'#EXTVLCOPT:http-referrer={REFERRER}\n'
            m3u_content += f'#EXTVLCOPT:http-origin={ORIGIN}\n'
            m3u_content += f'#EXTVLCOPT:http-user-agent={USER_AGENT}\n'
            m3u_content += f'{channel["url"]}\n'
    
    # Aggiungi il gruppo Soccer
    if "Soccer" in events_by_sport:
        for event in events_by_sport["Soccer"]:
            m3u_content += f'#EXTINF:-1 tvg-logo="{LOGO_URL}" group-title="Soccer",{event["event"]}\n'
            m3u_content += f'#EXTVLCOPT:http-referrer={REFERRER}\n'
            m3u_content += f'#EXTVLCOPT:http-origin={ORIGIN}\n'
            m3u_content += f'#EXTVLCOPT:http-user-agent={USER_AGENT}\n'
            m3u_content += f'{event["url"]}\n'
        del events_by_sport["Soccer"]  # Rimuovi Soccer per non duplicarlo
    
    # Aggiungi gli altri sport in ordine alfabetico
    for sport in sorted(events_by_sport.keys()):
        for event in events_by_sport[sport]:
            m3u_content += f'#EXTINF:-1 tvg-logo="{LOGO_URL}" group-title="{sport}",{event["event"]}\n'
            m3u_content += f'#EXTVLCOPT:http-referrer={REFERRER}\n'
            m3u_content += f'#EXTVLCOPT:http-origin={ORIGIN}\n'
            m3u_content += f'#EXTVLCOPT:http-user-agent={USER_AGENT}\n'
            m3u_content += f'{event["url"]}\n'
    
    return m3u_content

def main():
    html_content = scrape_page()
    if not html_content:
        return
    
    events_by_sport, italian_channels, calcio_italy_channels = parse_events(html_content)
    
    # Salva il file nella directory corrente
    m3u_file_path = "scheduleava.m3u8"
    
    # Genera e salva il file M3U
    m3u_content = generate_m3u(events_by_sport, italian_channels, calcio_italy_channels)
    with open(m3u_file_path, 'w', encoding='utf-8') as f:
        f.write(m3u_content)
    
    print(f"File M3U generato con successo: {m3u_file_path}")

if __name__ == "__main__":
    main()
