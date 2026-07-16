package com.minimoney.app.presentation.tasks

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.minimoney.app.domain.child.AgeBand
import com.minimoney.app.domain.child.ChildRepository
import com.minimoney.app.domain.core.AppError
import com.minimoney.app.domain.core.AppResult
import com.minimoney.app.domain.core.Clock
import com.minimoney.app.domain.core.MbuckCalculator
import com.minimoney.app.domain.dispute.Dispute
import com.minimoney.app.domain.dispute.DisputeRepository
import com.minimoney.app.domain.dispute.DisputeSla
import com.minimoney.app.domain.tasks.ChildTask
import com.minimoney.app.domain.tasks.EarnMode
import com.minimoney.app.domain.tasks.Frequency
import com.minimoney.app.domain.tasks.TaskRepository
import com.minimoney.app.domain.tasks.TaskTemplate
import com.minimoney.app.domain.tasks.templatesFor
import com.minimoney.app.domain.tasks.totalWeightFor
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class CreateTaskState(
    val visible: Boolean = false,
    /** Non-null while a preset is selected; the title/earn-mode/value/frequency fields mirror it. */
    val selectedTemplate: TaskTemplate? = null,
    val title: String = "",
    val earnMode: EarnMode = EarnMode.FIXED,
    val valueInput: String = "",
    val frequency: Frequency = Frequency.MONTHLY,
    val isSubmitting: Boolean = false,
    val error: AppError? = null,
    /** Frequency-adjusted, truncate-then-floor Mbuck preview (PERCENTAGE/TIER need a budget; FIXED never needs one). */
    val previewMbucks: Int? = null,
) {
    val canSubmit: Boolean
        get() = title.isNotBlank() && (valueInput.toIntOrNull() ?: 0) >= 1 && !isSubmitting

    /** TIER tasks draw from a shared tier pool — frequency is fixed by the preset, not parent-editable. */
    val frequencyLocked: Boolean
        get() = earnMode == EarnMode.TIER
}

@HiltViewModel
class TasksViewModel @Inject constructor(
    private val taskRepository: TaskRepository,
    private val disputeRepository: DisputeRepository,
    childRepository: ChildRepository,
    private val clock: Clock,
    savedStateHandle: SavedStateHandle,
) : ViewModel() {

    val childId: Long = checkNotNull(savedStateHandle["childId"])

    val tasks: StateFlow<List<ChildTask>> = taskRepository.tasksFor(childId)
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    val disputes: StateFlow<List<Dispute>> = disputeRepository.disputesFor(childId)
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    val child = childRepository.child(childId)
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), null)

    private val _createTask = MutableStateFlow(CreateTaskState())
    val createTask: StateFlow<CreateTaskState> = _createTask.asStateFlow()

    /** Presets for this child's age band only — a 6-9 chore list never shows up for a teenager. */
    val templates: StateFlow<List<TaskTemplate>> = child
        .map { it?.let { c -> templatesFor(c.ageBand) } ?: emptyList() }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    fun isDisputePastWindow(dispute: Dispute): Boolean =
        DisputeSla.isPastWindow(dispute.openedAtMillis, clock.nowMillis())

    fun onShowCreateTask() = _createTask.update { CreateTaskState(visible = true) }
    fun onDismissCreateTask() = _createTask.update { CreateTaskState() }
    fun onTitleChanged(value: String) = _createTask.update { it.copy(title = value, error = null) }

    /** Pass null to switch to manual/custom entry — clears the preset's fields. */
    fun onTemplateSelected(template: TaskTemplate?) {
        _createTask.update { state ->
            val next = if (template != null) {
                state.copy(
                    selectedTemplate = template,
                    title = template.title,
                    earnMode = EarnMode.TIER,
                    valueInput = template.relativeWeight.toString(),
                    frequency = template.tier,
                )
            } else {
                state.copy(
                    selectedTemplate = null,
                    title = "",
                    earnMode = EarnMode.FIXED,
                    valueInput = "",
                    frequency = Frequency.MONTHLY,
                )
            }
            next.copy(error = null, previewMbucks = preview(next))
        }
    }

    /** Manually changing the mode leaves preset territory — clears any selected template. */
    fun onEarnModeChanged(mode: EarnMode) {
        _createTask.update {
            val next = it.copy(selectedTemplate = null, earnMode = mode, valueInput = "")
            next.copy(previewMbucks = preview(next))
        }
    }

    fun onFrequencyChanged(frequency: Frequency) {
        _createTask.update { state ->
            if (state.frequencyLocked) return@update state // preset's tier isn't parent-editable
            val next = state.copy(frequency = frequency)
            next.copy(previewMbucks = preview(next))
        }
    }

    /** Digits only, in any mode — no decimal or fractional percentage can be typed. */
    fun onValueInputChanged(value: String) {
        if (value.length > 6 || !value.all(Char::isDigit)) return
        _createTask.update { state ->
            if (state.frequencyLocked) return@update state // a preset's weight isn't parent-editable
            val next = state.copy(valueInput = value, error = null)
            next.copy(previewMbucks = preview(next))
        }
    }

    /** Frequency-adjusted preview for any mode; PERCENTAGE/TIER additionally need a set budget. */
    private fun preview(state: CreateTaskState): Int? {
        val occurrences = state.frequency.occurrencesPerMonth
        return when (state.earnMode) {
            EarnMode.PERCENTAGE -> {
                val percent = state.valueInput.toIntOrNull()?.takeIf { it in 1..100 } ?: return null
                val budget = child.value?.budgetRand ?: return null
                MbuckCalculator.taskEarnValue(budget, percent, occurrences)
            }
            EarnMode.FIXED -> {
                val total = state.valueInput.toIntOrNull()?.takeIf { it >= 1 } ?: return null
                MbuckCalculator.taskEarnValueFixed(total, occurrences)
            }
            EarnMode.TIER -> {
                val weight = state.valueInput.toIntOrNull()?.takeIf { it >= 1 } ?: return null
                val budget = child.value?.budgetRand ?: return null
                val ageBand: AgeBand = child.value?.ageBand ?: return null
                val totalWeight = totalWeightFor(ageBand, state.frequency)
                if (totalWeight < weight) return null
                MbuckCalculator.tieredTaskEarnValue(
                    budget, state.frequency.tierBudgetSharePercent, weight, totalWeight, occurrences,
                )
            }
        }
    }

    fun onSubmitCreateTask() {
        val state = _createTask.value
        if (!state.canSubmit) return
        viewModelScope.launch {
            _createTask.update { it.copy(isSubmitting = true) }
            val result = taskRepository.createTask(
                childId = childId,
                title = state.title,
                earnMode = state.earnMode,
                earnValue = state.valueInput.toInt(),
                frequency = state.frequency,
            )
            when (result) {
                is AppResult.Success -> _createTask.update { CreateTaskState() }
                is AppResult.Failure -> _createTask.update {
                    it.copy(isSubmitting = false, error = result.error)
                }
            }
        }
    }

    fun onVerify(taskId: Long) = viewModelScope.launch { taskRepository.verify(taskId) }

    fun onOpenDispute(taskId: Long) = viewModelScope.launch {
        if (taskRepository.markDisputed(taskId) is AppResult.Success) {
            disputeRepository.open(taskId)
        }
    }

    fun onAcceptDispute(disputeId: Long) = viewModelScope.launch { disputeRepository.accept(disputeId) }
    fun onDeclineDispute(disputeId: Long) = viewModelScope.launch { disputeRepository.decline(disputeId) }
    fun onEscalateDispute(disputeId: Long) = viewModelScope.launch { disputeRepository.escalate(disputeId) }
}
