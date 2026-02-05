import math
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update
from bot.common.database.core import async_session_factory
from bot.common.database.models import User, Order

async def recalculate_rating(user_id: int):
    """
    Recalculates user rating based on all historical orders.
    Formula:
    weight = 1.0 (<=30d), 0.5 (31-90d), 0.2 (>90d)
    score = (weighted_good + 1) / (weighted_total + 2)
    confidence = 1 - exp(-total / 7)
    """
    async with async_session_factory() as session:
        # Fetch all orders for the user
        result = await session.execute(select(Order).where(Order.driver_id == user_id))
        orders = result.scalars().all()
        
        now = datetime.now(timezone.utc)
        weighted_good = 0.0
        weighted_total = 0.0
        raw_total_count = len(orders)
        
        for order in orders:
            # Ensure order.created_at is aware or fallback
            order_date = order.created_at
            if order_date.tzinfo is None:
                order_date = order_date.replace(tzinfo=timezone.utc)
            
            age_days = (now - order_date).days
            
            # Determine weight
            if age_days <= 30:
                weight = 1.0
            elif age_days <= 90:
                weight = 0.5
            else:
                weight = 0.2
            
            weighted_total += weight
            if order.is_good:
                weighted_good += (1.0 * weight)
            # if bad, add nothing to weighted_good, but add to total
        
        # Bayesian Smoothing with Prior for 4.0 start
        # We want initial score 0.75 (which maps to 4.0 stars: 1 + 4*0.75)
        # 0.75 = PRIOR_GOOD / PRIOR_TOTAL
        # Let's use PRIOR_TOTAL = 20, PRIOR_GOOD = 15
        PRIOR_GOOD = 15.0
        PRIOR_TOTAL = 20.0
        
        score = (weighted_good + PRIOR_GOOD) / (weighted_total + PRIOR_TOTAL)
        
        # Confidence
        # confidence = 1 - exp(-total / 7)
        confidence = 1 - math.exp(-raw_total_count / 7.0)
        
        # Update User
        stmt = update(User).where(User.user_id == user_id).values(
            rating_score=score,
            rating_confidence=confidence
        )
        await session.execute(stmt)
        await session.commit()

def get_star_rating(score: float) -> str:
    """
    Converts score (0..1) to stars string.
    Formula: stars = 1 + 4 * score
    """
    stars_val = 1 + 4 * score
    # Round to 1 decimal
    return f"{stars_val:.1f} ⭐️"

def get_rating_category(score: float) -> str:
    if score >= 0.85:
        return "Excellent 🟢"
    elif score >= 0.65:
        return "Normal 🟡"
    else:
        return "Issues 🔴"
