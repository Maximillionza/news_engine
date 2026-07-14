package com.minimoney.app.presentation.payslips

import androidx.lifecycle.SavedStateHandle
import com.minimoney.app.MainDispatcherRule
import com.minimoney.app.domain.core.AppError
import com.minimoney.app.domain.core.AppResult
import com.minimoney.app.domain.payslip.PayslipRepository
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.every
import io.mockk.mockk
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Rule
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class PayslipsViewModelTest {

    @get:Rule
    val mainDispatcherRule = MainDispatcherRule()

    private val repository: PayslipRepository = mockk(relaxed = true) {
        every { payslipsFor(1L) } returns flowOf(emptyList())
    }

    private fun viewModel() = PayslipsViewModel(repository, SavedStateHandle(mapOf("childId" to 1L)))

    @Test
    fun `generate with nothing to invoice surfaces the failure`() = runTest {
        coEvery { repository.generate(1L) } returns AppResult.Failure(AppError.Conflict)
        val vm = viewModel()
        vm.onGenerate()
        runCurrent()
        assertEquals(AppError.Conflict, vm.error.value)
    }

    @Test
    fun `successful generate clears any prior error`() = runTest {
        coEvery { repository.generate(1L) } returns AppResult.Success(9L)
        val vm = viewModel()
        vm.onGenerate()
        runCurrent()
        assertNull(vm.error.value)
    }

    @Test
    fun `confirm paid and penalty step delegate to the repository`() = runTest {
        coEvery { repository.confirmPaid(3L) } returns AppResult.Success(Unit)
        coEvery { repository.applyLatePenalty(3L, 1) } returns AppResult.Success(Unit)
        val vm = viewModel()

        vm.onConfirmPaid(3L)
        vm.onApplyPenaltyStep(3L)
        runCurrent()

        coVerify(exactly = 1) { repository.confirmPaid(3L) }
        // The cap itself is enforced in the repository (tested there); the VM
        // only ever requests single whole-Mbuck steps.
        coVerify(exactly = 1) { repository.applyLatePenalty(3L, 1) }
    }

    @Test
    fun `capped penalty rejection surfaces to the parent`() = runTest {
        coEvery { repository.applyLatePenalty(3L, 1) } returns AppResult.Failure(AppError.Conflict)
        val vm = viewModel()
        vm.onApplyPenaltyStep(3L)
        runCurrent()
        assertEquals(AppError.Conflict, vm.error.value)
    }
}
