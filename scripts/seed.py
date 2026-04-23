"""数据库初始化脚本（M7）。

用法:
    python scripts/seed.py

初始化:
    - 默认角色（ling）+ Live2D 配置
    - demo tenant + API key
"""

import asyncio
import os

from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "webling")

DEFAULT_CHARACTERS = [
    {
        "id": "ling",
        "name": "玲",
        "avatar_config": {
            "modelUrl": "/avatars/hiyori/hiyori_free_t08.model3.json",
            "scale": 0.9,
            "anchor": [0.5, 0.5],
            "motionMap": {},
            "autoBlink": True,
            "gazeMode": "mouse",
        },
        "greeting": "你好呀，我是玲。很高兴见到你。",
        "system_prompt": "你是玲，一个温柔可爱的虚拟助手。",
        "voice_id": None,
        "enabled": True,
    }
]

DEFAULT_TENANTS = [
    {
        "id": "demo",
        "api_key_hash": "3a5ab5c1e2c0e69a1e0e7db4a9deafd6ac30b4b86b2c50d6f49e9d4f6cc0432a",
        "allowed_origins": ["http://localhost:5173", "http://127.0.0.1:5173"],
        "character_whitelist": ["ling"],
        "daily_quota": 2000,
        "scope": ["chat", "embed"],
    }
]


async def seed_characters(db):
    for char in DEFAULT_CHARACTERS:
        existing = await db.characters.find_one({"id": char["id"]})
        if existing is None:
            await db.characters.insert_one(char)
            print(f"  + Created character: {char['id']}")
        else:
            print(f"  - Already exists: {char['id']}")


async def seed_tenants(db):
    for tenant in DEFAULT_TENANTS:
        existing = await db.tenants.find_one({"id": tenant["id"]})
        if existing is None:
            await db.tenants.insert_one(tenant)
            print(f"  + Created tenant: {tenant['id']}")
        else:
            print(f"  - Already exists: {tenant['id']}")


async def main():
    print(f"Connecting to MongoDB: {MONGO_URI}")
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[MONGO_DB]

    await client.admin.command("ping")
    print("MongoDB connection OK\n")

    print("Seeding characters...")
    await seed_characters(db)

    print("\nSeeding tenants...")
    await seed_tenants(db)

    print("\nSeed complete!")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
