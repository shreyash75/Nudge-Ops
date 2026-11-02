from fastapi import APIRouter, Depends

from app.core.auth import AuthenticatedUser, require_authenticated_user
from app.kubernetes.clusters import list_clusters
from app.models.schemas import ClusterListResponse

router = APIRouter(tags=["clusters"])


@router.get("/clusters", response_model=ClusterListResponse)
def get_clusters(
    _user: AuthenticatedUser = Depends(require_authenticated_user),
) -> ClusterListResponse:
    """Return every Kubernetes context available in the backend kubeconfig."""

    return list_clusters()
