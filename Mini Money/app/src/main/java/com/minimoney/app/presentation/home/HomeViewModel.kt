package com.minimoney.app.presentation.home

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.minimoney.app.data.db.LedgerDao
import com.minimoney.app.data.db.TaskDao
import com.minimoney.app.domain.child.AgeBand
import com.minimoney.app.domain.child.ChildLinkRepository
import com.minimoney.app.domain.child.ChildProfile
import com.minimoney.app.domain.child.ChildRepository
import com.minimoney.app.domain.child.MAX_CHILDREN_PER_PARENT
import com.minimoney.app.domain.core.AppError
import com.minimoney.app.domain.core.AppResult
import com.minimoney.app.domain.core.Clock
import com.minimoney.app.domain.flags.FeatureFlags
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.util.Calendar
import javax.inject.Inject

/** One row of the single-child view's "This week's tasks" list. */
data class HomeTaskRow(val id: Long, val title: String, val status: String, val mbuckValue: Int)

data class AddChildState(
    val visible: Boolean = false,
    val name: String = "",
    val ageBand: AgeBand? = null,
    /**
     * Optional — "can link", not "must link" (BuildSpec decision 2026-07-15).
     * Left blank, only the local ChildProfile is created, same as before this
     * feature existed. If set, the parent is also registering this email as
     * a pending Google-account link (supabase/functions/link-child) so that
     * device grants the child access once they sign in with it.
     */
    val childEmail: String = "",
    val isSubmitting: Boolean = false,
    val error: AppError? = null,
    /** Set only when the local child was created but the (optional) link registration failed. */
    val linkError: AppError? = null,
) {
    val canSubmit: Boolean get() = name.isNotBlank() && ageBand != null && !isSubmitting
}

@OptIn(ExperimentalCoroutinesApi::class)
@HiltViewModel
class HomeViewModel @Inject constructor(
    private val childRepository: ChildRepository,
    private val childLinkRepository: ChildLinkRepository,
    featureFlags: FeatureFlags,
    // DAOs directly for read-only aggregation (same precedent as MpointsViewModel).
    ledgerDao: LedgerDao,
    taskDao: TaskDao,
    clock: Clock,
) : ViewModel() {

    val children: StateFlow<List<ChildProfile>> = childRepository.children()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    /** Null = Family view; non-null = that child's single-child view (handoff §Screens 4-5). */
    private val _selectedChildId = MutableStateFlow<Long?>(null)
    val selectedChildId: StateFlow<Long?> = _selectedChildId.asStateFlow()

    fun onChildChipSelected(childId: Long?) {
        _selectedChildId.value = childId
    }

    /** Month-to-date earned Mbucks per child (calendar month of the injected clock). */
    val monthToDate: StateFlow<Map<Long, Int>> =
        ledgerDao.mbucksPerChildSince(startOfMonthMillis(clock.nowMillis()))
            .map { rows -> rows.associate { it.childId to it.total } }
            .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyMap())

    /** Tasks awaiting verification per child — the "{n} to verify" card badge. */
    val pendingVerify: StateFlow<Map<Long, Int>> = taskDao.pendingVerificationCounts()
        .map { rows -> rows.associate { it.childId to it.total } }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyMap())

    /** The selected child's task list for the single-child view. */
    val selectedChildTasks: StateFlow<List<HomeTaskRow>> = _selectedChildId
        .flatMapLatest { id ->
            if (id == null) flowOf(emptyList()) else taskDao.forChild(id)
        }
        .map { list -> list.map { HomeTaskRow(it.id, it.title, it.status, it.mbuckValue) } }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    /** Drives visibility of the linking entry point — hidden while the flag is OFF. */
    val accountLinkingEnabled: StateFlow<Boolean> = featureFlags.accountLinkingEnabled
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), false)

    private val _addChild = MutableStateFlow(AddChildState())
    val addChild: StateFlow<AddChildState> = _addChild.asStateFlow()

    val canAddChild: Boolean get() = children.value.size < MAX_CHILDREN_PER_PARENT

    fun onShowAddChild() = _addChild.update { AddChildState(visible = true) }
    fun onDismissAddChild() = _addChild.update { AddChildState() }
    fun onNameChanged(value: String) = _addChild.update { it.copy(name = value, error = null) }
    fun onAgeBandSelected(band: AgeBand) = _addChild.update { it.copy(ageBand = band) }
    fun onChildEmailChanged(value: String) = _addChild.update { it.copy(childEmail = value.trim(), linkError = null) }

    fun onSubmitAddChild() {
        val state = _addChild.value
        val band = state.ageBand ?: return
        if (!state.canSubmit) return
        viewModelScope.launch {
            _addChild.update { it.copy(isSubmitting = true, linkError = null) }
            when (val result = childRepository.createChild(state.name, band)) {
                is AppResult.Success -> {
                    if (state.childEmail.isBlank()) {
                        _addChild.update { AddChildState() }
                        return@launch
                    }
                    // Local profile exists either way — linking is a secondary,
                    // network-dependent step layered on top, not a rollback trigger.
                    when (val linkResult = childLinkRepository.linkChild(state.childEmail, state.name, band)) {
                        is AppResult.Success -> _addChild.update { AddChildState() }
                        is AppResult.Failure -> _addChild.update {
                            it.copy(isSubmitting = false, linkError = linkResult.error)
                        }
                    }
                }
                is AppResult.Failure -> _addChild.update {
                    it.copy(isSubmitting = false, error = result.error)
                }
            }
        }
    }
}

private fun startOfMonthMillis(nowMillis: Long): Long =
    Calendar.getInstance().apply {
        timeInMillis = nowMillis
        set(Calendar.DAY_OF_MONTH, 1)
        set(Calendar.HOUR_OF_DAY, 0)
        set(Calendar.MINUTE, 0)
        set(Calendar.SECOND, 0)
        set(Calendar.MILLISECOND, 0)
    }.timeInMillis
