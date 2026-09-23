from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from contextflow.api.schemas.requests import AssignRoleRequest, RevokeRoleRequest
from contextflow.auth.fastapi_deps import require_principal

router = APIRouter()


@router.post("/roles/assign")
def assign_role(
    request: Request, body: AssignRoleRequest, admin_principal: str = Depends(require_principal)
) -> dict:
    """Admin-only (in reality) but currently maps assignment to the policy engine."""
    policy_engine = request.app.state.engine.policy_engine
    if policy_engine is None:
        raise HTTPException(status_code=500, detail="PolicyEngine not configured")

    policy_engine.role_store.assign(body.principal, body.role)
    request.app.state.audit_log.record(
        admin_principal, "assign_role", {"target_principal": body.principal, "role": body.role}
    )
    return {
        "status": "success",
        "principal": body.principal,
        "roles": policy_engine.roles_for(body.principal),
    }


@router.post("/roles/revoke")
def revoke_role(
    request: Request, body: RevokeRoleRequest, admin_principal: str = Depends(require_principal)
) -> dict:
    policy_engine = request.app.state.engine.policy_engine
    if policy_engine is None:
        raise HTTPException(status_code=500, detail="PolicyEngine not configured")

    policy_engine.role_store.revoke(body.principal, body.role)
    request.app.state.audit_log.record(
        admin_principal, "revoke_role", {"target_principal": body.principal, "role": body.role}
    )
    return {
        "status": "success",
        "principal": body.principal,
        "roles": policy_engine.roles_for(body.principal),
    }


@router.get("/roles/{principal}")
def get_roles(
    principal: str, request: Request, caller_principal: str = Depends(require_principal)
) -> dict:
    policy_engine = request.app.state.engine.policy_engine
    if policy_engine is None:
        raise HTTPException(status_code=500, detail="PolicyEngine not configured")

    roles = policy_engine.roles_for(principal)
    return {"principal": principal, "roles": roles}
