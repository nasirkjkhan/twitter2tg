import httpx
from config import X_BEARER_TOKEN

BASE = "https://api.twitter.com/2"

HEADERS = {
    "Authorization": f"Bearer {X_BEARER_TOKEN}"
}

async def get_user_id(username):
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{BASE}/users/by/username/{username}",
            headers=HEADERS
        )
        r.raise_for_status()
        return r.json()["data"]["id"]

async def get_tweets(user_id, since_id=None):
    params = {
        "max_results": 5,
        "tweet.fields": "created_at,attachments",
        "expansions": "attachments.media_keys",
        "media.fields": "url,preview_image_url,type,variants"
    }

    if since_id:
        params["since_id"] = since_id

    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{BASE}/users/{user_id}/tweets",
            headers=HEADERS,
            params=params
        )
        r.raise_for_status()
        return r.json()

def extract_media(tweet, includes):
    media_urls = []
    video_url = None

    media_map = {
        m["media_key"]: m
        for m in includes.get("media", [])
    }

    for key in tweet.get("attachments", {}).get("media_keys", []):
        media = media_map.get(key)
        if not media:
            continue

        if media["type"] == "photo":
            media_urls.append(media.get("url"))

        if media["type"] in ["video", "animated_gif"]:
            variants = media.get("variants", [])
            mp4_variants = [
                v for v in variants
                if v.get("content_type") == "video/mp4"
            ]
            if mp4_variants:
                best = max(mp4_variants, key=lambda x: x.get("bit_rate", 0))
                video_url = best.get("url")

    return media_urls, video_url
