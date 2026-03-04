import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = {int(x.strip()) for x in os.getenv("ADMIN_IDS").split(",")}
X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN")
