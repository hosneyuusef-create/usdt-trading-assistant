"""
Configuration management service for Stage 22 (M22)
Handles versioned configuration storage, updates, and rollback
"""
import json
import hashlib
import secrets
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Tuple
from .schemas import (
    SystemConfiguration,
    ConfigurationVersion,
    ConfigurationUpdateRequest,
    ConfigurationHistoryEntry,
    RollbackRequest,
)

# Configuration store path
CONFIG_STORE_DIR = Path("config/versions")
CONFIG_STORE_DIR.mkdir(parents=True, exist_ok=True)

CURRENT_CONFIG_FILE = CONFIG_STORE_DIR / "current.json"
CONFIG_HISTORY_FILE = CONFIG_STORE_DIR / "history.json"


def _generate_rollback_token() -> str:
    """Generate a secure rollback token"""
    return secrets.token_urlsafe(32)


def _compute_config_hash(config: SystemConfiguration) -> str:
    """Compute SHA-256 hash of configuration for integrity"""
    config_dict = config.model_dump(mode="json")
    config_json = json.dumps(config_dict, sort_keys=True)
    return hashlib.sha256(config_json.encode()).hexdigest()


def _load_history() -> List[dict]:
    """Load configuration history from file"""
    if not CONFIG_HISTORY_FILE.exists():
        return []
    try:
        with open(CONFIG_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_history(history: List[dict]):
    """Save configuration history to file"""
    with open(CONFIG_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, default=str)


def get_current_configuration() -> Tuple[int, SystemConfiguration, datetime, str]:
    """
    Get the current active configuration
    Returns: (version, configuration, created_at, created_by)
    """
    if not CURRENT_CONFIG_FILE.exists():
        # Initialize with default configuration
        default_config = SystemConfiguration()
        version = 1
        created_at = datetime.utcnow()
        created_by = "system"
        rollback_token = _generate_rollback_token()

        config_version = ConfigurationVersion(
            version=version,
            configuration=default_config,
            created_at=created_at,
            created_by=created_by,
            rollback_token=rollback_token,
            change_reason="Initial system configuration"
        )

        # Save to current config file
        with open(CURRENT_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_version.model_dump(mode="json"), f, indent=2, default=str)

        # Save to history
        history = _load_history()
        history.append(config_version.model_dump(mode="json"))
        _save_history(history)

        return version, default_config, created_at, created_by

    # Load existing configuration
    with open(CURRENT_CONFIG_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    config_version = ConfigurationVersion(**data)
    return (
        config_version.version,
        config_version.configuration,
        config_version.created_at,
        config_version.created_by
    )


def update_configuration(request: ConfigurationUpdateRequest) -> ConfigurationVersion:
    """
    Update system configuration with a new version
    Returns the new configuration version
    """
    # Get current version
    current_version, _, _, _ = get_current_configuration()

    # Create new version
    new_version = current_version + 1
    rollback_token = _generate_rollback_token()

    config_version = ConfigurationVersion(
        version=new_version,
        configuration=request.configuration,
        created_at=datetime.utcnow(),
        created_by=request.created_by,
        rollback_token=rollback_token,
        change_reason=request.change_reason
    )

    # Save to current config file
    with open(CURRENT_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_version.model_dump(mode="json"), f, indent=2, default=str)

    # Append to history
    history = _load_history()
    history.append(config_version.model_dump(mode="json"))
    _save_history(history)

    # Log the change event
    _log_config_change_event(config_version)

    return config_version


def get_configuration_history() -> List[ConfigurationHistoryEntry]:
    """Get the full configuration history"""
    history = _load_history()
    return [
        ConfigurationHistoryEntry(
            version=entry["version"],
            created_at=datetime.fromisoformat(entry["created_at"]),
            created_by=entry["created_by"],
            change_reason=entry.get("change_reason"),
            rollback_token=entry["rollback_token"]
        )
        for entry in history
    ]


def get_configuration_by_version(version: int) -> Optional[ConfigurationVersion]:
    """Retrieve a specific configuration version"""
    history = _load_history()
    for entry in history:
        if entry["version"] == version:
            return ConfigurationVersion(**entry)
    return None


def rollback_configuration(request: RollbackRequest) -> Tuple[bool, int, int, str]:
    """
    Rollback configuration to a previous version
    Returns: (success, old_version, new_version, message)
    """
    # Get target version
    target_config = get_configuration_by_version(request.target_version)
    if not target_config:
        return False, 0, 0, f"Version {request.target_version} not found"

    # Verify rollback token
    if target_config.rollback_token != request.rollback_token:
        return False, 0, 0, "Invalid rollback token"

    # Get current version
    current_version, _, _, _ = get_current_configuration()

    # Create new version based on target configuration
    new_version = current_version + 1
    new_rollback_token = _generate_rollback_token()

    rollback_config_version = ConfigurationVersion(
        version=new_version,
        configuration=target_config.configuration,
        created_at=datetime.utcnow(),
        created_by=request.rollback_by,
        rollback_token=new_rollback_token,
        change_reason=f"Rollback to version {request.target_version}: {request.rollback_reason}"
    )

    # Save to current config file
    with open(CURRENT_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(rollback_config_version.model_dump(mode="json"), f, indent=2, default=str)

    # Append to history
    history = _load_history()
    history.append(rollback_config_version.model_dump(mode="json"))
    _save_history(history)

    # Log the rollback event
    _log_rollback_event(rollback_config_version, request.target_version)

    return True, current_version, new_version, f"Successfully rolled back from v{current_version} to v{request.target_version} (new version: v{new_version})"


def _log_config_change_event(config_version: ConfigurationVersion):
    """Log configuration change to audit log"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "config_events.json"

    event = {
        "event_type": "config_update",
        "version": config_version.version,
        "created_at": config_version.created_at.isoformat(),
        "created_by": config_version.created_by,
        "change_reason": config_version.change_reason,
        "config_hash": _compute_config_hash(config_version.configuration)
    }

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


def _log_rollback_event(config_version: ConfigurationVersion, target_version: int):
    """Log configuration rollback to audit log"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "config_events.json"

    event = {
        "event_type": "config_rollback",
        "new_version": config_version.version,
        "rolled_back_to": target_version,
        "created_at": config_version.created_at.isoformat(),
        "created_by": config_version.created_by,
        "rollback_reason": config_version.change_reason,
        "config_hash": _compute_config_hash(config_version.configuration)
    }

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


def validate_configuration(config: SystemConfiguration) -> Tuple[bool, List[str]]:
    """
    Validate configuration for business rules
    Returns: (is_valid, list_of_errors)
    """
    errors = []

    # Check scoring weights sum to 1.0
    if not config.scoring_weights.validate_sum():
        total = (config.scoring_weights.success_rate +
                 config.scoring_weights.on_time_settlement +
                 config.scoring_weights.dispute_ratio +
                 config.scoring_weights.manual_alerts)
        errors.append(f"Scoring weights must sum to 1.0 (current sum: {total:.3f})")

    # Check at least one network is allowed
    if not config.allowed_networks:
        errors.append("At least one blockchain network must be allowed")

    # Check settlement timeouts are reasonable
    if config.fiat_settlement_timeout_minutes < 5:
        errors.append("Fiat settlement timeout must be at least 5 minutes")
    if config.crypto_settlement_timeout_minutes < 5:
        errors.append("Crypto settlement timeout must be at least 5 minutes")

    return len(errors) == 0, errors
