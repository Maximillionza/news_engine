package com.minimoney.app.presentation.auth

import com.minimoney.app.MainDispatcherRule
import com.minimoney.app.domain.auth.AuthError
import com.minimoney.app.domain.auth.AuthRepository
import com.minimoney.app.domain.auth.AuthResult
import com.minimoney.app.domain.auth.ParentSession
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.mockk
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class AuthViewModelTest {

    @get:Rule
    val mainDispatcherRule = MainDispatcherRule()

    private val repository: AuthRepository = mockk(relaxed = true)

    private fun viewModel() = AuthViewModel(repository)

    @Test
    fun `sign-in started flags submitting and clears any prior error`() = runTest {
        val vm = viewModel()
        vm.onSignInFailed(AuthError.Network)
        vm.onSignInStarted()
        assertTrue(vm.uiState.value.isSubmitting)
        assertNull(vm.uiState.value.error)
    }

    @Test
    fun `successful token verify clears submitting with no error`() = runTest {
        // Routing after success is the session-driven root's job (AppViewModelTest);
        // this ViewModel's contract ends at a clean post-verify state.
        coEvery { repository.signInWithGoogle("id-token") } returns AuthResult.Success(
            ParentSession("acc-1", "tok", consentComplete = false),
        )
        val vm = viewModel()

        vm.onGoogleIdToken("id-token")
        runCurrent()

        assertFalse(vm.uiState.value.isSubmitting)
        assertNull(vm.uiState.value.error)
        coVerify(exactly = 1) { repository.signInWithGoogle("id-token") }
    }

    @Test
    fun `server rejection of the token surfaces as an error`() = runTest {
        coEvery { repository.signInWithGoogle(any()) } returns AuthResult.Failure(AuthError.Unknown())
        val vm = viewModel()

        vm.onGoogleIdToken("bad-token")
        runCurrent()

        assertFalse(vm.uiState.value.isSubmitting)
        assertTrue(vm.uiState.value.error is AuthError.Unknown)
    }

    @Test
    fun `Credential Manager cancellation never reaches the repository`() = runTest {
        val vm = viewModel()
        vm.onSignInStarted()
        vm.onSignInFailed(AuthError.SignInCancelled)

        assertEquals(AuthError.SignInCancelled, vm.uiState.value.error)
        assertFalse(vm.uiState.value.isSubmitting)
        coVerify(exactly = 0) { repository.signInWithGoogle(any()) }
    }
}
