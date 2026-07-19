"""Phase 10: Marketplace Registry (EMAS sec.7-10, sec.13), per EMAS sec.20's MVP Marketplace
Requirements (asset registry, search, validation workflow, version management, permission
control, evaluation tracking).
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from marketplace_service.models import AssetStatus, AssetType
from marketplace_service.registry import (
    AssetValidationError,
    average_evaluation_score,
    publish_asset,
    record_evaluation,
    retire_asset,
    search_assets,
    submit_asset,
    validate_asset,
)
from shared.db import Base, make_engine, make_session_factory


@pytest.fixture()
def session() -> Session:
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)
    with factory() as s:
        yield s


def _submit(session: Session, **overrides) -> str:
    defaults = dict(
        id="asset_security_review_agent_001",
        name="Security Review Agent",
        type=AssetType.AGENT_PACKAGE,
        version="1.0",
        description="Reviews code changes for security issues.",
        owner="engineering",
        capabilities=["security_analysis"],
        permissions=["read:repository"],
    )
    defaults.update(overrides)
    submit_asset(session, **defaults)
    return defaults["id"]


class TestAssetLifecycle:
    def test_full_lifecycle_submit_to_published(self, session: Session) -> None:
        asset_id = _submit(session)

        validated = validate_asset(session, asset_id)
        assert validated.status == AssetStatus.VALIDATED

        published = publish_asset(session, asset_id)
        assert published.status == AssetStatus.PUBLISHED

    def test_cannot_publish_before_validation(self, session: Session) -> None:
        asset_id = _submit(session)
        with pytest.raises(AssetValidationError):
            publish_asset(session, asset_id)

    def test_asset_with_no_permissions_fails_security_validation(self, session: Session) -> None:
        asset_id = _submit(session, id="asset_no_perms", permissions=[])
        with pytest.raises(AssetValidationError):
            validate_asset(session, asset_id)

    def test_retire_removes_asset_from_active_use(self, session: Session) -> None:
        asset_id = _submit(session)
        validate_asset(session, asset_id)
        publish_asset(session, asset_id)

        retired = retire_asset(session, asset_id)
        assert retired.status == AssetStatus.RETIRED


class TestSearchEMAS10:
    def test_search_finds_published_assets_by_name_and_capability(self, session: Session) -> None:
        published_id = _submit(session)
        validate_asset(session, published_id)
        publish_asset(session, published_id)

        unpublished_id = _submit(session, id="asset_unpublished", name="Unpublished Agent")

        by_name = search_assets(session, name_contains="Security")
        assert {a.id for a in by_name} == {published_id}

        by_capability = search_assets(session, capability="security_analysis")
        assert {a.id for a in by_capability} == {published_id}

        # Unpublished assets are excluded by default:
        assert unpublished_id not in {a.id for a in search_assets(session)}
        # But discoverable when explicitly asked for everything:
        assert unpublished_id in {a.id for a in search_assets(session, published_only=False)}


class TestEvaluationTrackingEMAS13:
    def test_evaluation_score_averages_across_multiple_ratings(self, session: Session) -> None:
        asset_id = _submit(session)
        validate_asset(session, asset_id)
        published = publish_asset(session, asset_id)

        assert average_evaluation_score(published) is None

        record_evaluation(session, asset_id, score=4.0)
        asset = record_evaluation(session, asset_id, score=2.0)

        assert average_evaluation_score(asset) == pytest.approx(3.0)
