import asyncio
import asyncpg
from bot.common.config import settings

async def main():
    print(f"Connecting to {settings.database_url}...")
    try:
        conn = await asyncpg.connect(settings.database_url.replace("postgresql+asyncpg://", "postgresql://"))
        print("Connected.")
        
        # 1. Check Triggers
        triggers = await conn.fetch("SELECT trigger_name FROM information_schema.triggers WHERE event_object_table = 'users'")
        print(f"Found Triggers: {[t['trigger_name'] for t in triggers]}")
        
        if not any(t['trigger_name'] == 'trigger_new_driver' for t in triggers):
            print("❌ CRITICAL: trigger_new_driver IS MISSING!")
        else:
            print("✅ trigger_new_driver exists.")

        # 2. Test Notification
        print("Sending test notification 'new_driver'...")
        # utilizing the notify_new_driver function or just manual notify
        # We need a valid user_id to test the admin bot logic completely, 
        # but let's just trigger the event first.
        # Use a dummy ID. Admin bot checks DB, so it might fail if ID doesn't exist.
        # Let's pick a user ID that likely exists (from logs: 2040216796)
        test_user_id = 2040216796
        await conn.execute(f"NOTIFY new_driver, '{test_user_id}';")
        print("Notification sent. Check admin_bot logs.")
        
        await conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
