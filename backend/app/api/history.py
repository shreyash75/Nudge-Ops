from fastapi import APIRouter, Depends

from app.core.auth import AuthenticatedUser, require_authenticated_user
from app.services.history import load_investigation_history

router = APIRouter(tags=["investigation-history"])


@router.get("/investigate/history")
def investigation_history(
    user: AuthenticatedUser = Depends(require_authenticated_user),
) -> list[dict]:
    """Return the user's investigation history stored in InsForge."""

    return load_investigation_history(user.id, user.email)
