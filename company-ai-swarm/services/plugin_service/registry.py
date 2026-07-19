"""Plugin Registry.

Source: Specifications/4 - future-expansion/Enterprise Plugin Architecture Specification
(EPAS).md sec.6 (Lifecycle), sec.8 (Validation Process: Schema Check -> Security Review ->
Capability Test -> Integration Test -> Approval -> Activation), sec.9 (Security Model),
sec.10 (Agent Plugin Access: Plugin Available -> Capability Match -> COO Approval -> Agent
Permission Granted -> Usage Logged).

Phase 10 scope (IMPLEMENTATION_PLAN.md, post-MVP Expansion Layer), per EPAS sec.18's own MVP
Plugin Requirements (registry, validation, tool/capability plugins, security controls, agent
access management):

- `register_plugin()` / `validate_plugin()` implement Schema Check (PluginType is an Enum -
  an invalid type fails at construction) and a minimal Security Review (security_level must
  be a known ESTAS Classification level). Capability Test and Integration Test (EPAS sec.8)
  require a real plugin runtime to execute against - none exists anywhere in this corpus
  (AgentDefinition.tools is still an untyped dict, Phase 4's own documented scope) - so those
  two gates are named here, not implemented, and validate_plugin() does not claim to perform
  them.
- `approve_plugin()` / `activate_plugin()` / `disable_plugin()` are explicit, human-triggered
  lifecycle transitions - no automatic approval exists anywhere in this corpus, consistent
  with every other approval-gated mechanism (orchestrator/escalation.py,
  memory_service/promotion.py).
- `grant_agent_access()` implements sec.10's last two steps only (Agent Permission Granted +
  Usage Logged, via the existing security_service/audit.py - no new audit mechanism).
  Capability Match and COO Approval (sec.10's first two steps) are the caller's
  responsibility; this function does not perform them, it only requires the plugin be ACTIVE.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from plugin_service.models import Plugin, PluginAccessGrant, PluginStatus, PluginType
from security_service.audit import write_audit_record
from shared.contracts import Classification


class PluginValidationError(Exception):
    pass


def register_plugin(
    session: Session,
    *,
    id: str,
    name: str,
    version: str,
    type: PluginType,
    owner: str,
    purpose: str,
    dependencies: list[str] | None = None,
    security_level: str = "internal",
) -> Plugin:
    plugin = Plugin(
        id=id,
        name=name,
        version=version,
        type=type,
        owner=owner,
        purpose=purpose,
        dependencies=dependencies or [],
        security_level=security_level,
        status=PluginStatus.REGISTERED,
    )
    session.add(plugin)
    session.commit()
    session.refresh(plugin)
    return plugin


def validate_plugin(session: Session, plugin_id: str) -> Plugin:
    plugin = session.get(Plugin, plugin_id)
    if plugin is None:
        raise ValueError(f"Unknown plugin: {plugin_id}")

    # Schema Check: PluginType already enforced at the column level (Enum) - re-checked here
    # so a bad value fails with a plugin-specific error, not a raw DB error.
    if plugin.type not in PluginType:
        raise PluginValidationError(f"Invalid plugin type: {plugin.type}")

    # Security Review (minimal): security_level must be a recognised classification.
    valid_levels = {c.value for c in Classification}
    if plugin.security_level not in valid_levels:
        raise PluginValidationError(
            f"Unknown security_level '{plugin.security_level}' - must be one of {valid_levels}"
        )

    plugin.status = PluginStatus.VALIDATED
    session.commit()
    session.refresh(plugin)
    return plugin


def approve_plugin(session: Session, plugin_id: str) -> Plugin:
    plugin = session.get(Plugin, plugin_id)
    if plugin is None:
        raise ValueError(f"Unknown plugin: {plugin_id}")
    if plugin.status != PluginStatus.VALIDATED:
        raise PluginValidationError(f"Plugin {plugin_id} must be VALIDATED before approval (is {plugin.status}).")
    plugin.status = PluginStatus.APPROVED
    session.commit()
    session.refresh(plugin)
    return plugin


def activate_plugin(session: Session, plugin_id: str) -> Plugin:
    plugin = session.get(Plugin, plugin_id)
    if plugin is None:
        raise ValueError(f"Unknown plugin: {plugin_id}")
    if plugin.status != PluginStatus.APPROVED:
        raise PluginValidationError(f"Plugin {plugin_id} must be APPROVED before activation (is {plugin.status}).")
    plugin.status = PluginStatus.ACTIVE
    session.commit()
    session.refresh(plugin)
    return plugin


def disable_plugin(session: Session, plugin_id: str) -> Plugin:
    plugin = session.get(Plugin, plugin_id)
    if plugin is None:
        raise ValueError(f"Unknown plugin: {plugin_id}")
    plugin.status = PluginStatus.DISABLED
    session.commit()
    session.refresh(plugin)
    return plugin


def grant_agent_access(session: Session, *, plugin_id: str, agent_id: str) -> PluginAccessGrant:
    plugin = session.get(Plugin, plugin_id)
    if plugin is None:
        raise ValueError(f"Unknown plugin: {plugin_id}")
    if plugin.status != PluginStatus.ACTIVE:
        raise PluginValidationError(f"Plugin {plugin_id} is not ACTIVE (is {plugin.status}) - cannot grant access.")

    grant = PluginAccessGrant(plugin_id=plugin_id, agent_id=agent_id)
    session.add(grant)
    session.commit()
    session.refresh(grant)

    write_audit_record(
        session,
        actor=agent_id,
        action=f"plugin_access_granted:{plugin_id}",
        decision="allowed",
        resource=f"plugin:{plugin_id}",
        reason="EPAS sec.10 Agent Plugin Access",
    )

    return grant


def agent_has_access(session: Session, *, plugin_id: str, agent_id: str) -> bool:
    return (
        session.query(PluginAccessGrant)
        .filter(PluginAccessGrant.plugin_id == plugin_id, PluginAccessGrant.agent_id == agent_id)
        .first()
        is not None
    )


def list_plugins(
    session: Session, *, status: PluginStatus | None = None, type: PluginType | None = None
) -> list[Plugin]:
    query = session.query(Plugin)
    if status is not None:
        query = query.filter(Plugin.status == status)
    if type is not None:
        query = query.filter(Plugin.type == type)
    return query.all()
