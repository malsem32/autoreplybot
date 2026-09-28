from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user
from backend.db.session import get_db
from backend.models.user import User
from backend.schemas.feature import ReferralStatsOut
from backend.services import referrals

router = APIRouter(prefix="/api/referrals", tags=["referrals"])


@router.get("", response_model=ReferralStatsOut)
async def get_referral_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReferralStatsOut:
    return ReferralStatsOut(**await referrals.referral_stats(db, user))
