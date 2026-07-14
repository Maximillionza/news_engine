package com.minimoney.app.presentation.tasks

import androidx.lifecycle.SavedStateHandle
import com.minimoney.app.MainDispatcherRule
import com.minimoney.app.domain.child.AgeBand
import com.minimoney.app.domain.child.ChildProfile
import com.minimoney.app.domain.child.ChildRepository
import com.minimoney.app.domain.core.Clock
import com.minimoney.app.domain.dispute.DisputeRepository
import com.minimoney.app.domain.tasks.EarnMode
import com.minimoney.app.domain.tasks.TaskRepository
import io.mockk.every
import io.mockk.mockk
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Rule
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class TasksViewModelTest {

    @get:Rule
    val mainDispatcherRule = MainDispatcherRule()

    private val taskRepository: TaskRepository = mockk(relaxed = true) {
        every { tasksFor(1L) } returns flowOf(emptyList())
    }
    private val disputeRepository: DisputeRepository = mockk(relaxed = true) {
        every { disputesFor(1L) } returns flowOf(emptyList())
    }

    private fun childRepo(budget: Int?): ChildRepository = mockk {
        every { child(1L) } returns flowOf(
            ChildProfile(1L, "acc-1", "T", AgeBand.TEN_TO_FOURTEEN, budget),
        )
    }

    private fun viewModel(budget: Int?) = TasksViewModel(
        taskRepository, disputeRepository, childRepo(budget), Clock { 0L },
        SavedStateHandle(mapOf("childId" to 1L)),
    )

    @Test
    fun `percentage preview applies truncate-then-floor`() = runTest {
        val vm = viewModel(budget = 199)
        backgroundScope.launch { vm.child.collect {} } // activate the stateIn upstream
        runCurrent()

        vm.onEarnModeChanged(EarnMode.PERCENTAGE)
        vm.onValueInputChanged("1") // 1.99 -> truncates to 1
        assertEquals(1, vm.createTask.value.percentagePreviewMbucks)
    }

    @Test
    fun `percentage preview floors zero to 1`() = runTest {
        val vm = viewModel(budget = 50)
        backgroundScope.launch { vm.child.collect {} }
        runCurrent()

        vm.onEarnModeChanged(EarnMode.PERCENTAGE)
        vm.onValueInputChanged("1") // 0.5 -> 0 -> floor 1
        assertEquals(1, vm.createTask.value.percentagePreviewMbucks)
    }

    @Test
    fun `no preview in fixed mode or without budget`() = runTest {
        val vm = viewModel(budget = null)
        backgroundScope.launch { vm.child.collect {} }
        runCurrent()

        vm.onValueInputChanged("5") // FIXED mode default
        assertNull(vm.createTask.value.percentagePreviewMbucks)

        vm.onEarnModeChanged(EarnMode.PERCENTAGE)
        vm.onValueInputChanged("5") // budget unset
        assertNull(vm.createTask.value.percentagePreviewMbucks)
    }

    @Test
    fun `value input rejects non-digits - no fractional percentage possible`() = runTest {
        val vm = viewModel(budget = 100)
        vm.onEarnModeChanged(EarnMode.PERCENTAGE)
        vm.onValueInputChanged("5")
        vm.onValueInputChanged("5.5") // ignored wholesale
        assertEquals("5", vm.createTask.value.valueInput)
    }
}
