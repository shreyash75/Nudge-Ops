from uuid import uuid4

from fastapi import APIRouter, Body, Depends, HTTPException, status

from app.core.auth import AuthenticatedUser, require_authenticated_user
from app.kubernetes.clusters import cluster_context_exists, current_context
from app.models.schemas import InvestigateRequest, InvestigateResponse
from app.services.history import save_investigation_history
from app.services.investigation import investigate_cluster
from app.services.progress import InvestigationProgressPublisher

router = APIRouter(tags=["investigation"])


@router.post("/investigate", response_model=InvestigateResponse)
def investigate(
    request: InvestigateRequest | None = Body(default=None),
    user: AuthenticatedUser = Depends(require_authenticated_user),
) -> InvestigateResponse:
    investigation_id = request.investigation_id if request else None
    response_id = str(investigation_id or uuid4())
    cluster = (request.cluster if request else None) or current_context()

    if cluster:
        exists, error = cluster_context_exists(cluster)
        if not exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error,
            )

    publisher = InvestigationProgressPublisher(response_id)

    try:
        result = investigate_cluster(
            cluster=cluster,
            progress_callback=publisher.publish,
        )
    finally:
        publisher.close()

    result.investigation_id = response_id
    save_investigation_history(user.id, result)
    return result
