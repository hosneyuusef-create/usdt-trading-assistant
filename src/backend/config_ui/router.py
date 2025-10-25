"""
Configuration UI Router for Stage 22 (M22)
Provides API endpoints for configuration management with RBAC
"""
from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
from datetime import datetime

from .schemas import (
    SystemConfiguration,
    ConfigurationUpdateRequest,
    ConfigurationHistoryResponse,
    ConfigurationHistoryEntry,
    RollbackRequest,
    RollbackResponse,
    CurrentConfigResponse,
)
from .service import (
    get_current_configuration,
    update_configuration,
    get_configuration_history,
    rollback_configuration,
    validate_configuration,
)
from ..security.rbac.policy import RBAC_POLICY
from ..security.rbac.dependencies import require_permission

router = APIRouter(prefix="/config", tags=["configuration"])


@router.get("/current", response_model=CurrentConfigResponse)
def get_current_config(
    _: None = Depends(require_permission("config:view"))
):
    """
    Get the current active system configuration
    Requires: config:view permission
    """
    version, configuration, created_at, created_by = get_current_configuration()

    # Check if this is the latest version
    history = get_configuration_history()
    is_latest = version == max([h.version for h in history]) if history else True

    return CurrentConfigResponse(
        version=version,
        configuration=configuration,
        created_at=created_at,
        created_by=created_by,
        is_latest=is_latest
    )


@router.post("/update", response_model=CurrentConfigResponse)
def update_config(
    request: ConfigurationUpdateRequest,
    _: None = Depends(require_permission("config:update"))
):
    """
    Update system configuration (creates a new version)
    Requires: config:update permission (Admin only)

    Note: Changes take effect immediately without requiring application restart
    """
    # Validate configuration
    is_valid, errors = validate_configuration(request.configuration)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Invalid configuration", "errors": errors}
        )

    # Update configuration
    config_version = update_configuration(request)

    return CurrentConfigResponse(
        version=config_version.version,
        configuration=config_version.configuration,
        created_at=config_version.created_at,
        created_by=config_version.created_by,
        is_latest=True
    )


@router.get("/history", response_model=ConfigurationHistoryResponse)
def get_config_history(
    _: None = Depends(require_permission("config:view"))
):
    """
    Get configuration change history
    Requires: config:view permission
    """
    history = get_configuration_history()

    if not history:
        return ConfigurationHistoryResponse(
            total_versions=0,
            current_version=0,
            history=[]
        )

    current_version = max([h.version for h in history])

    return ConfigurationHistoryResponse(
        total_versions=len(history),
        current_version=current_version,
        history=history
    )


@router.post("/rollback", response_model=RollbackResponse)
def rollback_config(
    request: RollbackRequest,
    _: None = Depends(require_permission("config:rollback"))
):
    """
    Rollback configuration to a previous version
    Requires: config:rollback permission (Admin only)

    Note: Rollback creates a new version with the configuration from the target version
    """
    success, old_version, new_version, message = rollback_configuration(request)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    return RollbackResponse(
        success=True,
        rolled_back_from=old_version,
        rolled_back_to=request.target_version,
        new_version=new_version,
        message=message
    )
