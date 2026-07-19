"""Marketplace Registry.

Source: Specifications/4 - future-expansion/Enterprise Marketplace Architecture
Specification (EMAS).md sec.7 (Lifecycle), sec.8 (Submission Process), sec.9 (Validation:
Technical/Security/Architecture/Performance), sec.10 (Search), sec.13 (Capability Ranking).

Phase 10 scope (IMPLEMENTATION_PLAN.md, post-MVP Expansion Layer), per EMAS sec.20's own MVP
Marketplace Requirements (asset registry, search, validation workflow, version management,
permission control, evaluation tracking):

- `validate_asset()` implements Architecture Validation ("Does it conform to enterprise
  rules?" - required fields present, type is a known AssetType) and a minimal Security
  Validation ("Is access controlled?" - permissions list is non-empty). Technical Validation
  ("Does it function?") and Performance Validation ("Does it deliver expected outcomes?")
  require executing the packaged asset and measuring it - no such runtime or metric exists
  anywhere in this corpus for an arbitrary packaged asset, so those two are named, not
  performed, same honesty as plugin_service.registry.py's Capability/Integration Test gates.
- `search_assets()` implements EMAS sec.10's "Name," "Capability," and "Department" (via
  `type`) discovery dimensions - "Performance," "Compatibility," and "Risk level" search are
  not implemented, since none of those are tracked anywhere on `MarketplaceAsset`.
- `record_evaluation()` is EMAS sec.13's Capability Ranking input: a running average, not a
  ranking algorithm - no ranking/weighting formula exists anywhere in this corpus.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from marketplace_service.models import AssetStatus, AssetType, MarketplaceAsset


class AssetValidationError(Exception):
    pass


def submit_asset(
    session: Session,
    *,
    id: str,
    name: str,
    type: AssetType,
    version: str,
    description: str,
    owner: str,
    capabilities: list[str] | None = None,
    requirements: list[str] | None = None,
    permissions: list[str] | None = None,
    dependencies: list[str] | None = None,
) -> MarketplaceAsset:
    asset = MarketplaceAsset(
        id=id,
        name=name,
        type=type,
        version=version,
        description=description,
        owner=owner,
        capabilities=capabilities or [],
        requirements=requirements or [],
        permissions=permissions or [],
        dependencies=dependencies or [],
        status=AssetStatus.SUBMITTED,
    )
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


def validate_asset(session: Session, asset_id: str) -> MarketplaceAsset:
    asset = session.get(MarketplaceAsset, asset_id)
    if asset is None:
        raise ValueError(f"Unknown asset: {asset_id}")

    # Architecture Validation:
    if asset.type not in AssetType:
        raise AssetValidationError(f"Invalid asset type: {asset.type}")
    if not asset.name or not asset.owner:
        raise AssetValidationError("Asset must have a name and an owner.")

    # Security Validation (minimal): access must be controlled by at least one permission.
    if not asset.permissions:
        raise AssetValidationError(
            f"Asset {asset_id} declares no permissions - access would be uncontrolled "
            f"(EMAS sec.9 Security Validation: 'Is access controlled?')."
        )

    asset.status = AssetStatus.VALIDATED
    session.commit()
    session.refresh(asset)
    return asset


def publish_asset(session: Session, asset_id: str) -> MarketplaceAsset:
    asset = session.get(MarketplaceAsset, asset_id)
    if asset is None:
        raise ValueError(f"Unknown asset: {asset_id}")
    if asset.status != AssetStatus.VALIDATED:
        raise AssetValidationError(f"Asset {asset_id} must be VALIDATED before publishing (is {asset.status}).")
    asset.status = AssetStatus.PUBLISHED
    session.commit()
    session.refresh(asset)
    return asset


def retire_asset(session: Session, asset_id: str) -> MarketplaceAsset:
    asset = session.get(MarketplaceAsset, asset_id)
    if asset is None:
        raise ValueError(f"Unknown asset: {asset_id}")
    asset.status = AssetStatus.RETIRED
    session.commit()
    session.refresh(asset)
    return asset


def record_evaluation(session: Session, asset_id: str, *, score: float) -> MarketplaceAsset:
    """EMAS sec.13 Capability Ranking input - see module docstring: a running average, not a
    ranking formula."""

    asset = session.get(MarketplaceAsset, asset_id)
    if asset is None:
        raise ValueError(f"Unknown asset: {asset_id}")

    asset.evaluation_count += 1
    asset.evaluation_score_total += score
    session.commit()
    session.refresh(asset)
    return asset


def average_evaluation_score(asset: MarketplaceAsset) -> float | None:
    if asset.evaluation_count == 0:
        return None
    return asset.evaluation_score_total / asset.evaluation_count


def search_assets(
    session: Session,
    *,
    name_contains: str | None = None,
    capability: str | None = None,
    type: AssetType | None = None,
    published_only: bool = True,
) -> list[MarketplaceAsset]:
    query = session.query(MarketplaceAsset)
    if published_only:
        query = query.filter(MarketplaceAsset.status == AssetStatus.PUBLISHED)
    if type is not None:
        query = query.filter(MarketplaceAsset.type == type)
    if name_contains is not None:
        query = query.filter(MarketplaceAsset.name.ilike(f"%{name_contains}%"))

    results = query.all()
    if capability is not None:
        results = [a for a in results if a.capabilities and capability in a.capabilities]
    return results
