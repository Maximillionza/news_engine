package com.minimoney.app.presentation.child

import androidx.lifecycle.SavedStateHandle
import com.minimoney.app.MainDispatcherRule
import com.minimoney.app.domain.child.ChildRepository
import com.minimoney.app.domain.core.AppResult
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.every
import io.mockk.mockk
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Rule
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class ChildDetailViewModelTest {

    @get:Rule
    val mainDispatcherRule = MainDispatcherRule()

    private val repository: ChildRepository = mockk(relaxed = true) {
        every { child(1L) } returns flowOf(null)
    }

    private fun viewModel() = ChildDetailViewModel(repository, SavedStateHandle(mapOf("childId" to 1L)))

    @Test
    fun `budget input ignores any edit containing a decimal point`() {
        val vm = viewModel()
        vm.onBudgetInputChanged("120")
        vm.onBudgetInputChanged("120.50") // must be ignored wholesale, not stripped
        assertEquals("120", vm.uiStateInput())
    }

    @Test
    fun `budget input ignores letters and signs`() {
        val vm = viewModel()
        vm.onBudgetInputChanged("12a")
        vm.onBudgetInputChanged("-5")
        assertEquals("", vm.uiStateInput())
    }

    @Test
    fun `zero budget cannot be submitted`() = runTest {
        val vm = viewModel()
        vm.onBudgetInputChanged("0")
        assertFalse(vm.budget.value.canSubmit)
        vm.onSubmitBudget()
        runCurrent()
        coVerify(exactly = 0) { repository.setBudget(any(), any()) }
    }

    @Test
    fun `valid whole-Rand budget submits as integer`() = runTest {
        coEvery { repository.setBudget(1L, 250) } returns AppResult.Success(Unit)
        val vm = viewModel()
        vm.onBudgetInputChanged("250")
        vm.onSubmitBudget()
        runCurrent()
        coVerify(exactly = 1) { repository.setBudget(1L, 250) }
    }

    private fun ChildDetailViewModel.uiStateInput() = budget.value.input
}
