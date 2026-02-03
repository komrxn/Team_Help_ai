from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from bot.common.config import settings

engine = create_async_engine(settings.database_url, echo=True)

async_session_factory = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)

class Base(DeclarativeBase):
    pass

async def get_session() -> AsyncSession:
    async with async_session_factory() as session:
        yield session

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        # Create Triggers explicitly using raw SQL
        # 1. Notify on New Driver
        await conn.execute(text("""
            CREATE OR REPLACE FUNCTION notify_new_driver() RETURNS TRIGGER AS $$
            BEGIN
                PERFORM pg_notify('new_driver', NEW.user_id::text);
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """))
        
        await conn.execute(text("DROP TRIGGER IF EXISTS trigger_new_driver ON users;"))
        await conn.execute(text("""
            CREATE TRIGGER trigger_new_driver
            AFTER INSERT ON users
            FOR EACH ROW
            EXECUTE FUNCTION notify_new_driver();
        """))

        # 2. Notify on Status Change (Active)
        await conn.execute(text("""
            CREATE OR REPLACE FUNCTION notify_user_status() RETURNS TRIGGER AS $$
            BEGIN
                IF NEW.status = 'active' AND OLD.status != 'active' THEN
                    PERFORM pg_notify('user_approved', NEW.user_id::text);
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """))
        
        await conn.execute(text("DROP TRIGGER IF EXISTS trigger_user_status ON users;"))
        await conn.execute(text("""
            CREATE TRIGGER trigger_user_status
            AFTER UPDATE ON users
            FOR EACH ROW
            EXECUTE FUNCTION notify_user_status();
        """))
