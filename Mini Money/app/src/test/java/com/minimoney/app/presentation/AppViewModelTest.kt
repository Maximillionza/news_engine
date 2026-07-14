package com.minimoney.app.presentation

import app.cash.turbine.test
import com.minimoney.app.MainDispatcherRule
import com.minimoney.app.domain.auth.AuthRepository
import com.minimoney.app.domain.auth.ParentSession
import io.mockk.every
import io.mockk.mockk
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test

/**
 * The consent gate lives here: destination is a pure function of session
 * state, so these tests pin the only routing rules in the app.
 */
class AppViewModelTest {

    @get:Rule
    val mainDispatcherRule = MainDispatcherRule()

    private val sessionFlow = MutableStateFlow<ParentSession?>(null)
    private val repository: AuthRepository = mockk {
        every { session } returns sessionFlow
    }

    @Test
    fun `starts at LOADING then routes by session state`() = runTest {
        val vm = AppViewModel(repository)
        vm.destination.test {
            assertEquals(RootDestination.LOADING, awaitItem())
            assertEquals(RootDestination.AUTH, awaitItem())

            // Verified but unconsented parent must land on consent, never home.
            sessionFlow.value = ParentSession("acc-1", "tok", consentComplete = false)
            assertEquals(RootDestination.CONSENT, awaitItem())

            sessionFlow.value = ParentSession("acc-1", "tok", consentComplete = true)
            assertEquals(RootDestination.HOME, awaitItem())

            // Sign-out from anywhere falls back to auth.
            sessionFlow.value = null
            assertEquals(RootDestination.AUTH, awaitItem())
        }
    }
}
