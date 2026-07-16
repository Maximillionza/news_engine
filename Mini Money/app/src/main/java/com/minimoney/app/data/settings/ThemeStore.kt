package com.minimoney.app.data.settings

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.preferencesDataStore
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

private val Context.themeDataStore: DataStore<Preferences> by preferencesDataStore(
    // Own file, separate from the session store: sign-out clears the session
    // but must not flip the user's theme back.
    name = "app_theme",
)

/** Persists the Profile > Dark mode toggle. Null = no choice yet, follow the system. */
@Singleton
class ThemeStore @Inject constructor(
    @ApplicationContext private val context: Context,
) {
    private object Keys {
        val darkMode = booleanPreferencesKey("dark_mode")
    }

    val darkMode: Flow<Boolean?> = context.themeDataStore.data.map { it[Keys.darkMode] }

    suspend fun setDarkMode(enabled: Boolean) {
        context.themeDataStore.edit { it[Keys.darkMode] = enabled }
    }
}
