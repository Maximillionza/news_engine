"""Phase 10: Plugin Registry (EPAS sec.6-10), per EPAS sec.18's MVP Plugin Requirements
(registry, validation, tool/capability plugins, security controls, agent access management).
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from plugin_service.models import PluginStatus, PluginType
from plugin_service.registry import (
    PluginValidationError,
    activate_plugin,
    agent_has_access,
    approve_plugin,
    disable_plugin,
    grant_agent_access,
    list_plugins,
    register_plugin,
    validate_plugin,
)
from security_service.audit import get_audit_trail
from shared.db import Base, make_engine, make_session_factory


@pytest.fixture()
def session() -> Session:
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)
    with factory() as s:
        yield s


def _register(session: Session, **overrides) -> str:
    defaults = dict(
        id="plugin_dev_tools_001",
        name="Developer Tools Plugin",
        version="1.0",
        type=PluginType.TOOL,
        owner="engineering",
        purpose="Static analysis and linting for the Engineering Department.",
    )
    defaults.update(overrides)
    register_plugin(session, **defaults)
    return defaults["id"]


class TestPluginLifecycle:
    def test_full_lifecycle_register_to_active(self, session: Session) -> None:
        plugin_id = _register(session)

        validated = validate_plugin(session, plugin_id)
        assert validated.status == PluginStatus.VALIDATED

        approved = approve_plugin(session, plugin_id)
        assert approved.status == PluginStatus.APPROVED

        active = activate_plugin(session, plugin_id)
        assert active.status == PluginStatus.ACTIVE

    def test_cannot_approve_before_validation(self, session: Session) -> None:
        plugin_id = _register(session)
        with pytest.raises(PluginValidationError):
            approve_plugin(session, plugin_id)

    def test_cannot_activate_before_approval(self, session: Session) -> None:
        plugin_id = _register(session)
        validate_plugin(session, plugin_id)
        with pytest.raises(PluginValidationError):
            activate_plugin(session, plugin_id)

    def test_unrecognized_security_level_fails_validation(self, session: Session) -> None:
        plugin_id = _register(session, id="plugin_bad_001", security_level="ultra_secret")
        with pytest.raises(PluginValidationError):
            validate_plugin(session, plugin_id)

    def test_disable_removes_a_plugin_from_active_use(self, session: Session) -> None:
        plugin_id = _register(session)
        validate_plugin(session, plugin_id)
        approve_plugin(session, plugin_id)
        activate_plugin(session, plugin_id)

        disabled = disable_plugin(session, plugin_id)
        assert disabled.status == PluginStatus.DISABLED


class TestAgentPluginAccessEPAS10:
    def test_access_requires_an_active_plugin(self, session: Session) -> None:
        plugin_id = _register(session)  # still REGISTERED, not ACTIVE

        with pytest.raises(PluginValidationError):
            grant_agent_access(session, plugin_id=plugin_id, agent_id="engineering_agent_001")

    def test_granted_access_is_queryable_and_logged(self, session: Session) -> None:
        plugin_id = _register(session)
        validate_plugin(session, plugin_id)
        approve_plugin(session, plugin_id)
        activate_plugin(session, plugin_id)

        assert agent_has_access(session, plugin_id=plugin_id, agent_id="engineering_agent_001") is False

        grant_agent_access(session, plugin_id=plugin_id, agent_id="engineering_agent_001")

        assert agent_has_access(session, plugin_id=plugin_id, agent_id="engineering_agent_001") is True
        trail = get_audit_trail(session, "engineering_agent_001")
        assert any(r.action.startswith("plugin_access_granted") for r in trail)


class TestPluginDiscovery:
    def test_list_plugins_filters_by_status_and_type(self, session: Session) -> None:
        tool_id = _register(session, id="plugin_a", type=PluginType.TOOL)
        capability_id = _register(session, id="plugin_b", type=PluginType.CAPABILITY)
        validate_plugin(session, tool_id)

        assert {p.id for p in list_plugins(session)} == {tool_id, capability_id}
        assert {p.id for p in list_plugins(session, type=PluginType.CAPABILITY)} == {capability_id}
        assert {p.id for p in list_plugins(session, status=PluginStatus.VALIDATED)} == {tool_id}
