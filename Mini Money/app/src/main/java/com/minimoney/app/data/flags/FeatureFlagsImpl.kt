package com.minimoney.app.data.flags

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.preferencesDataStore
import com.minimoney.app.domain.flags.FeatureFlags
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

// Own DataStore file: flags are config, not session state — signing out must
// never reset a regulatory flag.
private val Context.flagsDataStore: DataStore<Preferences> by preferencesDataStore(
    name = "feature_flags",
)

@Singleton
class FeatureFlagsImpl @Inject constructor(
    @ApplicationContext context: Context,
) : FeatureFlags {

    private val dataStore = context.flagsDataStore

    private object Keys {
        val accountLinking = booleanPreferencesKey("ACCOUNT_LINKING_ENABLED")
        val mpoints = booleanPreferencesKey("MPOINTS_ENABLED")
    }

    // Absent key = false: OFF is the default state, not a stored value, so a
    // fresh install is always in the launch-compliant configuration.
    override val accountLinkingEnabled: Flow<Boolean> =
        dataStore.data.map { it[Keys.accountLinking] ?: false }

    override val mpointsEnabled: Flow<Boolean> =
        dataStore.data.map { it[Keys.mpoints] ?: false }

    override suspend fun setAccountLinkingEnabled(enabled: Boolean) {
        dataStore.edit { it[Keys.accountLinking] = enabled }
    }

    override suspend fun setMpointsEnabled(enabled: Boolean) {
        dataStore.edit { it[Keys.mpoints] = enabled }
    }
}
