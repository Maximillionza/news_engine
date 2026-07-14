package com.minimoney.app.domain.child

/** Three-tier cohort model (PRD §Personas); the six-way split is explicitly not adopted. */
enum class AgeBand { SIX_TO_NINE, TEN_TO_FOURTEEN, FIFTEEN_TO_EIGHTEEN }

data class ChildProfile(
    val id: Long,
    val parentAccountId: String,
    val displayName: String,
    val ageBand: AgeBand,
    /** Whole Rand, integer only — no cents exists anywhere (BuildSpec §Data Model, Budget). */
    val budgetRand: Int?,
)

/** 1 parent : up to 4 children (PRD §Product Summary). Enforced at profile creation. */
const val MAX_CHILDREN_PER_PARENT = 4
