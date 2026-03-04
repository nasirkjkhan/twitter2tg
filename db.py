import aiosqlite

DB = "bot.db"

async def init():
    async with aiosqlite.connect(DB) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS usernames (
            username TEXT PRIMARY KEY,
            last_id TEXT
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """)
        await db.commit()

async def add_username(username):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT OR IGNORE INTO usernames(username,last_id) VALUES(?, '')",
            (username,)
        )
        await db.commit()

async def remove_username(username):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "DELETE FROM usernames WHERE username=?",
            (username,)
        )
        await db.commit()

async def get_usernames():
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT username,last_id FROM usernames")
        return await cur.fetchall()

async def update_last_id(username, tweet_id):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "UPDATE usernames SET last_id=? WHERE username=?",
            (tweet_id, username)
        )
        await db.commit()

async def get_setting(key, default=""):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT value FROM settings WHERE key=?", (key,))
        row = await cur.fetchone()
        return row[0] if row else default

async def set_setting(key, value):
    async with aiosqlite.connect(DB) as db:
        await db.execute("""
        INSERT INTO settings(key,value)
        VALUES(?,?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """, (key, value))
        await db.commit()
