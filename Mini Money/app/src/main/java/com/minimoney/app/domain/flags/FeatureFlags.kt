package com.minimoney.app.domain.flags

import kotlinx.coroutines.flow.Flow

/**
 * Config-level (not build-time) flags, both OFF by default at launch
 * (BuildSpec §Architecture). ACCOUNT_LINKING awaits the SARB/NPS Act recheck;
 * MPOINTS awaits the FPB recheck. The app must run correctly in all three
 * configurations (full / no-linking / no-Mpoints) — QA tests all three.
 */
interface FeatureFlags {
    val accountLinkingEnabled: Flow<Boolean>
    val mpointsEnabled: Flow<Boolean>

    suspend fun setAccountLinkingEnabled(enabled: Boolean)
    suspend fun setMpointsEnabled(enabled: Boolean)
}
