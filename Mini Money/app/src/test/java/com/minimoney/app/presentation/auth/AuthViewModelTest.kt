package com.minimoney.app.presentation.auth

import com.minimoney.app.MainDispatcherRule
import com.minimoney.app.domain.auth.AuthError
import com.minimoney.app.domain.auth.AuthRepository
import com.minimoney.app.domain.auth.AuthResult
import com.minimoney.app.domain.auth.OtpChallenge
import com.minimoney.app.domain.auth.ParentSession
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.mockk
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.advanceTimeBy
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class AuthViewModelTest {

    @get:Rule
    val mainDispatcherRule = MainDispatcherRule()

    private val repository: AuthRepository = mockk(relaxed = true)

    private val challenge = OtpChallenge(
        challengeId = "ch-1",
        phoneE164 = "+27821234567",
        expiresInSeconds = 300,
        resendAllowedInSeconds = 30,
    )

    private fun viewModel() = AuthViewModel(repository)

    @Test
    fun `invalid phone flags error and never calls network`() = runTest {
        val vm = viewModel()
        vm.onPhoneChanged("12345")
        vm.onSubmitPhone()
        runCurrent()

        assertTrue(vm.uiState.value.phoneInvalid)
        assertEquals(AuthStage.PHONE, vm.uiState.value.stage)
        coVerify(exactly = 0) { repository.requestOtp(any()) }
    }

    @Test
    fun `valid phone advances to OTP stage with masked number and countdown`() = runTest {
        coEvery { repository.requestOtp("+27821234567") } returns AuthResult.Success(challenge)
        val vm = viewModel()

        vm.onPhoneChanged("082 123 4567")
        vm.onSubmitPhone()
        runCurrent()

        val state = vm.uiState.value
        assertEquals(AuthStage.OTP, state.stage)
        assertEquals("+27••••••567", state.maskedPhone)
        assertEquals(30, state.resendSecondsRemaining)
    }

    @Test
    fun `verify success clears submitting with no error`() = runTest {
        // Routing after success is the session-driven root's job (AppViewModelTest);
        // this ViewModel's contract ends at a clean post-verify state.
        coEvery { repository.requestOtp(any()) } returns AuthResult.Success(challenge)
        coEvery { repository.verifyOtp("ch-1", "123456") } returns AuthResult.Success(
            ParentSession("acc-1", "tok", consentComplete = false),
        )
        val vm = viewModel()
        vm.onPhoneChanged("0821234567")
        vm.onSubmitPhone()
        runCurrent()

        vm.onOtpChanged("123456")
        vm.onSubmitOtp()
        runCurrent()

        assertEquals(false, vm.uiState.value.isSubmitting)
        assertNull(vm.uiState.value.error)
        coVerify(exactly = 1) { repository.verifyOtp("ch-1", "123456") }
    }

    @Test
    fun `otp mismatch surfaces error and stays on OTP stage`() = runTest {
        coEvery { repository.requestOtp(any()) } returns AuthResult.Success(challenge)
        coEvery { repository.verifyOtp(any(), any()) } returns
            AuthResult.Failure(AuthError.OtpMismatch)
        val vm = viewModel()
        vm.onPhoneChanged("0821234567")
        vm.onSubmitPhone()
        runCurrent()

        vm.onOtpChanged("000000")
        vm.onSubmitOtp()
        runCurrent()

        assertEquals(AuthError.OtpMismatch, vm.uiState.value.error)
        assertEquals(AuthStage.OTP, vm.uiState.value.stage)
    }

    @Test
    fun `resend is blocked during countdown and allowed after`() = runTest {
        coEvery { repository.requestOtp(any()) } returns AuthResult.Success(challenge)
        val vm = viewModel()
        vm.onPhoneChanged("0821234567")
        vm.onSubmitPhone()
        runCurrent()

        vm.onResendOtp() // countdown at 30s — must be ignored
        runCurrent()
        coVerify(exactly = 1) { repository.requestOtp(any()) }

        advanceTimeBy(31_000)
        runCurrent()
        assertEquals(0, vm.uiState.value.resendSecondsRemaining)

        vm.onResendOtp()
        runCurrent()
        coVerify(exactly = 2) { repository.requestOtp(any()) }
    }

    @Test
    fun `otp input is digit-filtered and capped at six`() = runTest {
        val vm = viewModel()
        vm.onOtpChanged("12ab34cd5678x9")
        assertEquals("123456", vm.uiState.value.otpInput)
    }

    @Test
    fun `edit phone resets to phone stage and clears challenge state`() = runTest {
        coEvery { repository.requestOtp(any()) } returns AuthResult.Success(challenge)
        val vm = viewModel()
        vm.onPhoneChanged("0821234567")
        vm.onSubmitPhone()
        runCurrent()

        vm.onEditPhone()
        runCurrent()

        val state = vm.uiState.value
        assertEquals(AuthStage.PHONE, state.stage)
        assertEquals("", state.otpInput)
        assertEquals(0, state.resendSecondsRemaining)
        assertNull(state.error)

        // With the challenge abandoned, submit/resend are inert.
        vm.onOtpChanged("123456")
        vm.onSubmitOtp()
        vm.onResendOtp()
        runCurrent()
        coVerify(exactly = 0) { repository.verifyOtp(any(), any()) }
        coVerify(exactly = 1) { repository.requestOtp(any()) }
    }
}
