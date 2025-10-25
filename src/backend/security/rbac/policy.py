from __future__ import annotations

from typing import Dict, Iterable, List, Set, Tuple

# Stage 12 RBAC policy definitions. Actions follow the pattern "<resource>:<verb>".
RBAC_POLICY: Dict[str, Set[str]] = {
    "admin": {
        "customer:register",
        "customer:view",
        "provider:register",
        "provider:view",
        "rfq:create",
        "rfq:update",
        "rfq:cancel",
        "rfq:view",
        "notification:broadcast",
        "quote:view",
        "award:execute",
        "award:view",
        "award:manual_override",
        "settlement:start",
        "settlement:view",
        "settlement:verify",
        "partial_fill:reallocate",
        "partial_fill:cancel",
        "partial_fill:view",
        "dispute:file",
        "dispute:submit_evidence",
        "dispute:get",
        "dispute:list",
        "dispute:get_evidence",
        "dispute:review",
        "dispute:decide",
        "dispute:escalate",
        "config:view",
        "config:update",
        "config:rollback",
        "rbac:read",
    },
    "operations": {
        "customer:register",
        "provider:register",
        "provider:view",
        "rfq:create",
        "rfq:update",
        "rfq:cancel",
        "rfq:view",
        "notification:broadcast",
        "quote:view",
        "award:execute",
        "award:view",
        "settlement:start",
        "settlement:view",
        "settlement:verify",
        "partial_fill:reallocate",
        "partial_fill:cancel",
        "partial_fill:view",
        "config:view",
        "rbac:read",
    },
    "compliance": {
        "provider:view",
        "rfq:view",
        "quote:view",
        "award:view",
        "settlement:view",
        "partial_fill:view",
        "rbac:read",
    },
    "customer": {
        "customer:register",
        "rfq:create",
        "rfq:view",
        "dispute:file",
        "dispute:submit_evidence",
        "dispute:get",
    },
    "provider": {
        "rfq:view",
        "quote:submit",
        "settlement:submit_evidence",
        "dispute:file",
        "dispute:submit_evidence",
        "dispute:get",
    },
}

ROLE_DESCRIPTIONS: Dict[str, str] = {
    "admin": "Full administrative access including provider onboarding and RBAC review.",
    "operations": "Operations desk with authority to onboard customers/providers and monitor eligibility.",
    "compliance": "Compliance analysts with read-only access to provider information and RBAC policy.",
    "customer": "End-customer interactions limited to self-service registration.",
    "provider": "Liquidity providers with quote submission capability.",
}

ACTION_DESCRIPTIONS: Dict[str, str] = {
    "customer:register": "Create or update customer KYC profiles.",
    "customer:view": "Read customer information (future stages).",
    "provider:register": "Create or update provider eligibility records.",
    "provider:view": "List or inspect provider eligibility status.",
    "rfq:create": "Create new RFQ with timing and special conditions.",
    "rfq:update": "Modify existing RFQ details prior to expiry/award.",
    "rfq:cancel": "Cancel an open RFQ and trigger audit logging.",
    "rfq:view": "Retrieve RFQ data for monitoring or compliance.",
    "notification:broadcast": "Dispatch RFQ notifications to eligible providers.",
    "quote:submit": "Submit quote responses to RFQs within allowed timeframe.",
    "quote:view": "List or audit submitted quotes.",
    "award:execute": "Run award engine and confirm winning quotes.",
    "award:view": "Inspect award outcomes and audit traces.",
    "award:manual_override": "Manually override award selection for a specific quote.",
    "settlement:start": "Initialise settlement workflow for awarded quotes.",
    "settlement:view": "Review settlement legs and status.",
    "settlement:verify": "Verify submitted settlement evidence or escalate.",
    "settlement:submit_evidence": "Upload settlement evidence for a specific leg.",
    "partial_fill:reallocate": "Reallocate award portions between providers.",
    "partial_fill:cancel": "Cancel or mark failing legs for reallocation.",
    "partial_fill:view": "Inspect partial-fill status and reconciliation.",
    "dispute:file": "File a new dispute on a settlement.",
    "dispute:submit_evidence": "Submit evidence for a dispute within the evidence window.",
    "dispute:get": "Retrieve dispute details and current status.",
    "dispute:list": "List all disputes with optional status filter.",
    "dispute:get_evidence": "View evidence submissions for a dispute.",
    "dispute:review": "Start arbitration review process on a dispute.",
    "dispute:decide": "Make arbitration decision and resolve dispute.",
    "dispute:escalate": "Escalate dispute to higher authority.",
    "config:view": "View current system configuration and history.",
    "config:update": "Update system configuration (creates new version).",
    "config:rollback": "Rollback configuration to a previous version.",
    "rbac:read": "Read RBAC matrix and audit entries.",
}


def list_policy_matrix() -> Tuple[List[str], List[str], Dict[Tuple[str, str], bool]]:
    """
    Return the RBAC matrix in (roles, actions, mapping) form.
    """

    roles = sorted(RBAC_POLICY.keys())
    actions: Set[str] = set()
    for role_actions in RBAC_POLICY.values():
        actions.update(role_actions)
    ordered_actions = sorted(actions)

    matrix: Dict[Tuple[str, str], bool] = {}
    for role in roles:
        for action in ordered_actions:
            matrix[(role, action)] = action in RBAC_POLICY[role]
    return roles, ordered_actions, matrix
