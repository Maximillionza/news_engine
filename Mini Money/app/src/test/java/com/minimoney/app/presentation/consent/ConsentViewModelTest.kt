package com.minimoney.app.presentation.consent

import com.minimoney.app.MainDispatcherRule
import com.minimoney.app.domain.auth.AuthRepository
import com.minimoney.app.domain.consent.ConsentAcceptance
import com.minimoney.app.domain.consent.ConsentDocument
import com.minimoney.app.domain.consent.ConsentRepository
import com.minimoney.app.domain.consent.ConsentSection
import com.minimoney.app.domain.core.AppError
import com.minimoney.app.domain.core.AppResult
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
class ConsentViewModelTest {

    @get:Rule
    val mainDispatcherRule = MainDispatcherRule()

    private val consentRepository: ConsentRepository = mockk()
    private val authRepository: AuthRepository = mockk(relaxed = true)

    private val document = ConsentDocument(
        version = "v1",
        sections = listOf(ConsentSection("Data we process", "...")),
    )

    private fun viewModel() = ConsentViewModel(consentRepository, authRepository)

    @Test
    fun `loads document on init`() = runTest {
        coEvery { consentRepository.getCurrentDocument() } returns AppResult.Success(document)
        val vm = viewModel()
        runCurrent()

        assertEquals(document, vm.uiState.value.document)
        assertFalse(vm.uiState.value.isLoading)
    }

    @Test
    fun `load failure surfaces error and retry recovers`() = runTest {
        coEvery { consentRepository.getCurrentDocument() } returns
            AppResult.Failure(AppError.Network)
        val vm = viewModel()
        runCurrent()
        assertEquals(AppError.Network, vm.uiState.value.loadError)

        coEvery { consentRepository.getCurrentDocument() } returns AppResult.Success(document)
        vm.onRetry()
        runCurrent()
        assertNull(vm.uiState.value.loadError)
        assertEquals(document, vm.uiState.value.document)
    }

    @Test
    fun `accept is inert until acknowledgement is checked`() = runTest {
        coEvery { consentRepository.getCurrentDocument() } returns AppResult.Success(document)
        val vm = viewModel()
        runCurrent()

        vm.onAccept()
        runCurrent()
        coVerify(exactly = 0) { consentRepository.acceptConsent(any()) }

        vm.onAckToggled(true)
        assertTrue(vm.uiState.value.canAccept)
    }

    @Test
    fun `accept submits the loaded document version`() = runTest {
        coEvery { consentRepository.getCurrentDocument() } returns AppResult.Success(document)
        coEvery { consentRepository.acceptConsent("v1") } returns
            AppResult.Success(ConsentAcceptance("v1", 1_000L))
        val vm = viewModel()
        runCurrent()

        vm.onAckToggled(true)
        vm.onAccept()
        runCurrent()

        coVerify(exactly = 1) { consentRepository.acceptConsent("v1") }
        assertFalse(vm.uiState.value.isSubmitting)
        assertNull(vm.uiState.value.submitError)
    }

    @Test
    fun `version conflict reloads the document and resets acknowledgement`() = runTest {
        coEvery { consentRepository.getCurrentDocument() } returns AppResult.Success(document)
        coEvery { consentRepository.acceptConsent("v1") } returns
            AppResult.Failure(AppError.Conflict)
        val vm = viewModel()
        runCurrent()

        vm.onAckToggled(true)
        vm.onAccept()
        runCurrent()

        // Re-consent against the new text: document refetched, ack cleared.
        coVerify(exactly = 2) { consentRepository.getCurrentDocument() }
        assertFalse(vm.uiState.value.ackChecked)
    }

    @Test
    fun `submit failure surfaces error without reload`() = runTest {
        coEvery { consentRepository.getCurrentDocument() } returns AppResult.Success(document)
        coEvery { consentRepository.acceptConsent("v1") } returns
            AppResult.Failure(AppError.Network)
        val vm = viewModel()
        runCurrent()

        vm.onAckToggled(true)
        vm.onAccept()
        runCurrent()

        assertEquals(AppError.Network, vm.uiState.value.submitError)
        coVerify(exactly = 1) { consentRepository.getCurrentDocument() }
    }

    @Test
    fun `decline signs out`() = runTest {
        coEvery { consentRepository.getCurrentDocument() } returns AppResult.Success(document)
        val vm = viewModel()
        runCurrent()

        vm.onDecline()
        runCurrent()
        coVerify(exactly = 1) { authRepository.signOut() }
    }
}
