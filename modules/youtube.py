import re
import requests

YOUTUBE_API_KEY = "AIzaSyATLJHb5eDZHZU9hkO3x2eBzx2f9LqItbI"
CHANNELS = ["#paris", "#montreal", "#kodi"]
MASTER = "alxd"

enabled = True

def toggle(nick):
    global enabled
    if nick.lower() != MASTER.lower():
        return f"Désolé {nick}, tu n'as pas la permission."
    enabled = not enabled
    return f"Module YouTube {'activé' if enabled else 'désactivé'}"

def scan(nick, chan, text):
    if not enabled:
        return None
    if chan.lower() not in [c.lower() for c in CHANNELS]:
        return None

    match = re.search(r"(?:youtu\\.be/|youtube\\.com/watch\\?v=)([A-Za-z0-9_-]+)", text)
    if not match:
        return None

    video_id = match.group(1)
    return announce(video_id)

def announce(video_id):
    url = (
        "https://www.googleapis.com/youtube/v3/videos"
        "?id={}&key={}&part=snippet,statistics"
    ).format(video_id, YOUTUBE_API_KEY)

    r = requests.get(url)
    data = r.json()

    try:
        item = data["items"][0]
        title = item["snippet"]["title"]
        channel = item["snippet"]["channelTitle"]
        views = item["statistics"]["viewCount"]
        return f"📺 YouTube → {title} — par {channel} — {views} vues"
    except:
        return "Impossible de récupérer les infos YouTube."
