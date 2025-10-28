import requests

# URL sorgente M3U
url = "https://raw.githubusercontent.com/nzo66/TV/refs/heads/main/mpd.m3u"

# Ordine gruppi desiderato
group_order = [
    "Sport",
    "Film- Serie TV",
    "Documentari",
    "Bambini",
    "Altro",
    "Rai",
    "Mediaset",
    "News",
    "Musica"
]

# Scarica la playlist
print("Scarico la playlist...")
response = requests.get(url)
response.raise_for_status()
lines = response.text.strip().splitlines()

# Parsing canali
channels = []
current_info = None

for line in lines:
    if line.startswith("#EXTINF"):
        current_info = line
    elif line.startswith("http"):
        if current_info:
            channels.append((current_info, line))
            current_info = None

# Raggruppa per gruppo
groups = {name: [] for name in group_order}
groups["Altro"] = []  # fallback per canali senza gruppo

for info, link in channels:
    group_name = "Altro"
    if 'group-title="' in info:
        group_name = info.split('group-title="')[1].split('"')[0]
    if group_name not in groups:
        group_name = "Altro"
    groups[group_name].append((info, link))

# Scrivi nuova playlist ordinata
output_file = "SkyMPD.m3u8"
with open(output_file, "w", encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for group in group_order:
        if groups[group]:
            f.write(f"\n# ---- {group} ----\n")
            for info, link in groups[group]:
                f.write(f"{info}\n{link}\n")

print(f"✅ Playlist ordinata salvata come: {output_file}")
