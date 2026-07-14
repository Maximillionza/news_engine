package com.minimoney.app.data.auth

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import com.minimoney.app.domain.auth.ParentSession
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Persists the parent session. All three fields must be present to form a
 * session — a partial write (e.g. process death mid-edit) reads back as
 * signed out rather than as a corrupt half-session.
 */
@Singleton
class SessionStore @Inject constructor(
    private val dataStore: DataStore<Preferences>,
) {
    private object Keys {
        val accountId = stringPreferencesKey("parent_account_id")
        val accessToken = stringPreferencesKey("access_token")
        val consentComplete = booleanPreferencesKey("consent_complete")
    }

    val session: Flow<ParentSession?> = dataStore.data.map { prefs ->
        val id = prefs[Keys.accountId]
        val token = prefs[Keys.accessToken]
        val consent = prefs[Keys.consentComplete]
        if (id != null && token != null && consent != null) {
            ParentSession(parentAccountId = id, accessToken = token, consentComplete = consent)
        } else {
            null
        }
    }

    suspend fun save(session: ParentSession) {
        dataStore.edit { prefs ->
            prefs[Keys.accountId] = session.parentAccountId
            prefs[Keys.accessToken] = session.accessToken
            prefs[Keys.consentComplete] = session.consentComplete
        }
    }

    /** Flips consent on the persisted session after a successful acceptance. */
    suspend fun markConsentComplete() {
        dataStore.edit { prefs ->
            if (prefs[Keys.accountId] != null) prefs[Keys.consentComplete] = true
        }
    }

    suspend fun clear() {
        dataStore.edit { it.clear() }
    }
}
