import requests
import re

# URL sorgente M3U
url = "https://raw.githubusercontent.com/nzo66/TV/refs/heads/main/mpd.m3u"

# Ordine gruppi desiderato
group_order = [
    "Film - Serie TV",
    "Sport",
    "Documentari",
    "Bambini",
    "Altro",
    "Rai",
    "Mediaset",
    "News",
    "Musica"
]

# Funzione per normalizzare i nomi dei gruppi
def normalize_group_name(name):
    return name.strip().lower().replace(" ", "").replace("-", "").replace("_", "")

# Funzione per formattare i nomi dei canali
def format_channel_name(name):
    # Rimuove "(MPD)" o simili (insensibile a maiuscole/minuscole)
    name = re.sub(r"\(.*?mpd.*?\)", "", name, flags=re.IGNORECASE)
    # Rimuove spazi multipli
    name = re.sub(r"\s+", " ", name.strip())
    # Rende la prima lettera di ogni parola maiuscola
    return " ".join(word.capitalize() for word in name.split(" "))

normalized_order = [normalize_group_name(g) for g in group_order]

print("🔄 Scarico la playlist...")
response = requests.get(url)
response.raise_for_status()
lines = response.text.strip().splitlines()

# Parsing canali
channels = []
current_block = []

for line in lines:
    if line.startswith("#EXTINF:"):
        if current_block:
            channels.append(current_block)
        current_block = [line]
    elif line.startswith("#") or line.startswith("http"):
        current_block.append(line)

if current_block:
    channels.append(current_block)

# Raggruppa i canali
groups = {name: [] for name in group_order}
groups["Altro"] = []

for block in channels:
    first_line = block[0]
    match = re.search(r'group-title="([^"]+)"', first_line)
    if match:
        group_name = match.group(1).strip()
    else:
        group_name = "Altro"

    norm_name = normalize_group_name(group_name)
    if norm_name in normalized_order:
        index = normalized_order.index(norm_name)
        target_group = group_order[index]
    else:
        target_group = "Altro"

    # Estrae il nome del canale e lo formatta
    title_match = re.search(r'#EXTINF:.*?,(.*)', first_line)
    if title_match:
        channel_name = format_channel_name(title_match.group(1))
        # Ricostruisce la riga con il nome formattato
        first_line = re.sub(r'#EXTINF:.*?,.*', f'#EXTINF:-1 {first_line.split(" ", 1)[1].split(",", 1)[0]}, {channel_name}', first_line)

    block[0] = first_line
    groups[target_group].append(block)

# Scrittura ordinata
output_file = "SkyMPD.m3u8"
with open(output_file, "w", encoding="utf-8") as f:
    f.write("#EXTM3U\n\n")
    for group in group_order:
        if groups[group]:
            f.write(f"# ===== {group} =====\n")
            for block in groups[group]:
                for line in block:
                    f.write(f"{line}\n")
                f.write("\n")

print(f"✅ Playlist completa e ordinata salvata come: {output_file}")
