package com.minimoney.app.presentation.tasks

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.minimoney.app.domain.tasks.ChildTask
import com.minimoney.app.domain.tasks.TaskRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

/**
 * Child-facing surface: completion marking only. No verification, no
 * disputes, no payslip data, and — by the terminology-governance rule — every
 * string this screen renders comes from strings_child.xml.
 */
@HiltViewModel
class ChildTasksViewModel @Inject constructor(
    private val taskRepository: TaskRepository,
    savedStateHandle: SavedStateHandle,
) : ViewModel() {

    val childId: Long = checkNotNull(savedStateHandle["childId"])

    val tasks: StateFlow<List<ChildTask>> = taskRepository.tasksFor(childId)
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    fun onMarkDone(taskId: Long) = viewModelScope.launch { taskRepository.markCompleted(taskId) }
}
