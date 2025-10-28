import requests

# URL sorgente M3U
url = "https://raw.githubusercontent.com/nzo66/TV/refs/heads/main/mpd.m3u"

# Ordine gruppi desiderato
group_order = [
    "Film- Serie TV",
    "Sport",
    "Documentari",
    "Bambini",
    "Altro",
    "Rai",
    "Mediaset",
    "News",
    "Musica"
]

# Scarica la playlist
print("🔄 Scarico la playlist...")
response = requests.get(url)
response.raise_for_status()
lines = response.text.strip().splitlines()

# Parsing canali (con tutte le righe)
channels = []
current_block = []

for line in lines:
    if line.startswith("#EXTINF:"):
        # Se c'è un blocco precedente, lo salviamo
        if current_block:
            channels.append(current_block)
            current_block = []
        current_block = [line]
    elif line.startswith("#") or line.startswith("http"):
        current_block.append(line)

# Aggiunge l'ultimo blocco se esiste
if current_block:
    channels.append(current_block)

# Raggruppa per gruppo
groups = {name: [] for name in group_order}
groups["Altro"] = []  # fallback per canali senza gruppo

for block in channels:
    first_line = block[0]
    group_name = "Altro"
    if 'group-title="' in first_line:
        group_name = first_line.split('group-title="')[1].split('"')[0]
    if group_name not in groups:
        group_name = "Altro"
    groups[group_name].append(block)

# Scrive nuova playlist ordinata
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
