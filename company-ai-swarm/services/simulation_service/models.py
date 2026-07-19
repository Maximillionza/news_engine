"""Simulation Run persistence.

Source: Specifications/1 - enterprise-architecture/Enterprise Simulation & Digital Twin
Specification (ESDTS).md sec.14:

    simulation_input: objective, starting_state, variables, constraints, assumptions,
                       success_metrics
    simulation_output: scenario, predicted_results, risks, advantages, limitations,
                        confidence, recommendation

ESDTS sec.14 itself states this schema "supersedes the two other independently-drafted
variants found in the source documents" - it is the canonical one to implement, so both
input and output are modeled literally here, on one persisted row (SimulationRun) for
traceability rather than two.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from shared.db import Base


class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True)

    # simulation_input:
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    starting_state: Mapped[dict] = mapped_column(JSON, nullable=False)
    variables: Mapped[dict] = mapped_column(JSON, nullable=False)
    constraints: Mapped[dict] = mapped_column(JSON, nullable=False)
    assumptions: Mapped[list] = mapped_column(JSON, nullable=False)
    success_metrics: Mapped[list] = mapped_column(JSON, nullable=False)

    # simulation_output:
    scenario: Mapped[str] = mapped_column(String, nullable=False)
    predicted_results: Mapped[dict] = mapped_column(JSON, nullable=False)
    risks: Mapped[list] = mapped_column(JSON, nullable=False)
    advantages: Mapped[list] = mapped_column(JSON, nullable=False)
    limitations: Mapped[list] = mapped_column(JSON, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
