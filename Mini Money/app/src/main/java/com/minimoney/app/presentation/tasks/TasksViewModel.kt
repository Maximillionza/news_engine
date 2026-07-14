package com.minimoney.app.presentation.tasks

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
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
import com.minimoney.app.domain.tasks.TaskRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class CreateTaskState(
    val visible: Boolean = false,
    val title: String = "",
    val earnMode: EarnMode = EarnMode.FIXED,
    val valueInput: String = "",
    val isSubmitting: Boolean = false,
    val error: AppError? = null,
    /** PERCENTAGE mode: the truncate-then-floor Mbuck preview, or null without a budget. */
    val percentagePreviewMbucks: Int? = null,
) {
    val canSubmit: Boolean
        get() = title.isNotBlank() && (valueInput.toIntOrNull() ?: 0) >= 1 && !isSubmitting
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

    fun isDisputePastWindow(dispute: Dispute): Boolean =
        DisputeSla.isPastWindow(dispute.openedAtMillis, clock.nowMillis())

    fun onShowCreateTask() = _createTask.update { CreateTaskState(visible = true) }
    fun onDismissCreateTask() = _createTask.update { CreateTaskState() }
    fun onTitleChanged(value: String) = _createTask.update { it.copy(title = value, error = null) }

    fun onEarnModeChanged(mode: EarnMode) {
        _createTask.update { it.copy(earnMode = mode, valueInput = "", percentagePreviewMbucks = null) }
    }

    /** Digits only, in both modes — no decimal or fractional percentage can be typed. */
    fun onValueInputChanged(value: String) {
        if (value.length > 6 || !value.all(Char::isDigit)) return
        _createTask.update { state ->
            state.copy(
                valueInput = value,
                error = null,
                percentagePreviewMbucks = percentagePreview(state.earnMode, value),
            )
        }
    }

    private fun percentagePreview(mode: EarnMode, input: String): Int? {
        if (mode != EarnMode.PERCENTAGE) return null
        val percent = input.toIntOrNull()?.takeIf { it in 1..100 } ?: return null
        val budget = child.value?.budgetRand ?: return null
        return MbuckCalculator.taskEarnValue(budget, percent)
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
