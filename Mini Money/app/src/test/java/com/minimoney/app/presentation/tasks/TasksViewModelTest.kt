package com.minimoney.app.presentation.tasks

import androidx.lifecycle.SavedStateHandle
import com.minimoney.app.MainDispatcherRule
import com.minimoney.app.domain.child.AgeBand
import com.minimoney.app.domain.child.ChildProfile
import com.minimoney.app.domain.child.ChildRepository
import com.minimoney.app.domain.core.Clock
import com.minimoney.app.domain.dispute.DisputeRepository
import com.minimoney.app.domain.tasks.EarnMode
import com.minimoney.app.domain.tasks.Frequency
import com.minimoney.app.domain.tasks.TASK_TEMPLATES
import com.minimoney.app.domain.tasks.TaskRepository
import com.minimoney.app.domain.tasks.templatesFor
import com.minimoney.app.domain.tasks.totalWeightFor
import io.mockk.every
import io.mockk.mockk
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
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

    private fun childRepo(budget: Int?, ageBand: AgeBand = AgeBand.TEN_TO_FOURTEEN): ChildRepository = mockk {
        every { child(1L) } returns flowOf(ChildProfile(1L, "acc-1", "T", ageBand, budget))
    }

    private fun viewModel(budget: Int?, ageBand: AgeBand = AgeBand.TEN_TO_FOURTEEN) = TasksViewModel(
        taskRepository, disputeRepository, childRepo(budget, ageBand), Clock { 0L },
        SavedStateHandle(mapOf("childId" to 1L)),
    )

    private fun TestScope.activate(vm: TasksViewModel) = backgroundScope.launch { vm.child.collect {} }

    @Test
    fun `percentage preview applies truncate-then-floor`() = runTest {
        val vm = viewModel(budget = 199)
        activate(vm)
        runCurrent()

        vm.onEarnModeChanged(EarnMode.PERCENTAGE)
        vm.onValueInputChanged("1") // 1.99 -> truncates to 1
        assertEquals(1, vm.createTask.value.previewMbucks)
    }

    @Test
    fun `percentage preview floors zero to 1`() = runTest {
        val vm = viewModel(budget = 50)
        activate(vm)
        runCurrent()

        vm.onEarnModeChanged(EarnMode.PERCENTAGE)
        vm.onValueInputChanged("1") // 0.5 -> 0 -> floor 1
        assertEquals(1, vm.createTask.value.previewMbucks)
    }

    @Test
    fun `fixed mode never needs a budget but percentage mode does`() = runTest {
        val vm = viewModel(budget = null)
        activate(vm)
        runCurrent()

        vm.onValueInputChanged("5") // FIXED mode default, no budget required
        assertEquals(5, vm.createTask.value.previewMbucks)

        vm.onEarnModeChanged(EarnMode.PERCENTAGE)
        vm.onValueInputChanged("5") // budget unset
        assertNull(vm.createTask.value.previewMbucks)
    }

    @Test
    fun `value input rejects non-digits - no fractional percentage possible`() = runTest {
        val vm = viewModel(budget = 100)
        vm.onEarnModeChanged(EarnMode.PERCENTAGE)
        vm.onValueInputChanged("5")
        vm.onValueInputChanged("5.5") // ignored wholesale
        assertEquals("5", vm.createTask.value.valueInput)
    }

    @Test
    fun `templates are filtered to the child's age band`() = runTest {
        val vm = viewModel(budget = 1000, ageBand = AgeBand.SIX_TO_NINE)
        activate(vm)
        runCurrent()
        backgroundScope.launch { vm.templates.collect {} }
        runCurrent()

        assertEquals(templatesFor(AgeBand.SIX_TO_NINE), vm.templates.value)
        assertFalse(vm.templates.value.any { it.ageBand != AgeBand.SIX_TO_NINE })
    }

    @Test
    fun `selecting a template pre-fills title, TIER mode, its relative weight and locked tier`() = runTest {
        val vm = viewModel(budget = 1000)
        activate(vm)
        runCurrent()

        val template = TASK_TEMPLATES.first { it.ageBand == AgeBand.TEN_TO_FOURTEEN }
        vm.onTemplateSelected(template)

        val state = vm.createTask.value
        assertEquals(template, state.selectedTemplate)
        assertEquals(template.title, state.title)
        assertEquals(EarnMode.TIER, state.earnMode)
        assertEquals(template.relativeWeight.toString(), state.valueInput)
        assertEquals(template.tier, state.frequency)
        assertEquals(true, state.frequencyLocked)
    }

    @Test
    fun `switching back to custom clears the selected template and resets to FIXED`() = runTest {
        val vm = viewModel(budget = 1000)
        vm.onTemplateSelected(TASK_TEMPLATES.first { it.ageBand == AgeBand.TEN_TO_FOURTEEN })
        vm.onTemplateSelected(null)
        assertNull(vm.createTask.value.selectedTemplate)
        assertEquals("", vm.createTask.value.title)
        assertEquals(EarnMode.FIXED, vm.createTask.value.earnMode)
    }

    @Test
    fun `manually changing earn mode drops any selected template`() = runTest {
        val vm = viewModel(budget = 1000)
        vm.onTemplateSelected(TASK_TEMPLATES.first { it.ageBand == AgeBand.TEN_TO_FOURTEEN })
        vm.onEarnModeChanged(EarnMode.FIXED)
        assertNull(vm.createTask.value.selectedTemplate)
    }

    @Test
    fun `a locked template's tier and weight cannot be edited via the normal setters`() = runTest {
        val vm = viewModel(budget = 1000)
        val template = TASK_TEMPLATES.first { it.ageBand == AgeBand.TEN_TO_FOURTEEN && it.tier == Frequency.WEEKLY }
        vm.onTemplateSelected(template)

        vm.onFrequencyChanged(Frequency.DAILY) // must be ignored — locked
        vm.onValueInputChanged("999") // must be ignored — locked

        assertEquals(template.tier, vm.createTask.value.frequency)
        assertEquals(template.relativeWeight.toString(), vm.createTask.value.valueInput)
    }

    @Test
    fun `tier preview matches budget times tier share times weight share divided by occurrences`() = runTest {
        val vm = viewModel(budget = 3000, ageBand = AgeBand.TEN_TO_FOURTEEN)
        activate(vm)
        runCurrent()

        val template = TASK_TEMPLATES.first { it.title == "Homework completed on time" }
        vm.onTemplateSelected(template)

        // 40% daily tier of 3000 = 1200; weight 5 of totalWeight 10 -> 600; / 30 occurrences = 20
        val totalWeight = totalWeightFor(AgeBand.TEN_TO_FOURTEEN, Frequency.DAILY)
        assertEquals(10, totalWeight)
        assertEquals(20, vm.createTask.value.previewMbucks)
    }

    @Test
    fun `daily frequency divides the percentage preview across 30 occurrences`() = runTest {
        val vm = viewModel(budget = 3000)
        activate(vm)
        runCurrent()

        vm.onEarnModeChanged(EarnMode.PERCENTAGE)
        vm.onValueInputChanged("30") // 30% of 3000 = 900 monthly total
        vm.onFrequencyChanged(Frequency.DAILY) // 900 / 30 = 30 per day
        assertEquals(30, vm.createTask.value.previewMbucks)
    }

    @Test
    fun `weekly frequency divides the fixed preview across the 4point3 occurrence assumption`() = runTest {
        val vm = viewModel(budget = null)
        vm.onValueInputChanged("100") // FIXED mode, 100 Mbucks total per month
        vm.onFrequencyChanged(Frequency.WEEKLY) // 100 / 4.3 = 23.25... -> truncates to 23
        assertEquals(23, vm.createTask.value.previewMbucks)
    }
}
