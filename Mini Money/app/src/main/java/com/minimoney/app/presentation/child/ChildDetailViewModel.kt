package com.minimoney.app.presentation.child

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.minimoney.app.domain.child.ChildProfile
import com.minimoney.app.domain.child.ChildRepository
import com.minimoney.app.domain.core.AppError
import com.minimoney.app.domain.core.AppResult
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class BudgetInputState(
    val input: String = "",
    val isSubmitting: Boolean = false,
    val error: AppError? = null,
) {
    val canSubmit: Boolean get() = (input.toIntOrNull() ?: 0) > 0 && !isSubmitting
}

@HiltViewModel
class ChildDetailViewModel @Inject constructor(
    private val childRepository: ChildRepository,
    savedStateHandle: SavedStateHandle,
) : ViewModel() {

    val childId: Long = checkNotNull(savedStateHandle["childId"])

    val child: StateFlow<ChildProfile?> = childRepository.child(childId)
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), null)

    private val _budget = MutableStateFlow(BudgetInputState())
    val budget: StateFlow<BudgetInputState> = _budget.asStateFlow()

    /**
     * Whole-Rand-only, enforced at the validation layer (BuildSpec
     * §Screens/Flows 5): an edit containing anything but digits — including a
     * decimal point — is ignored outright, not stripped or reformatted. There
     * is no code path by which a cents value can reach the repository.
     */
    fun onBudgetInputChanged(value: String) {
        if (value.length <= 7 && value.all(Char::isDigit)) {
            _budget.update { it.copy(input = value, error = null) }
        }
    }

    fun onSubmitBudget() {
        val amount = _budget.value.input.toIntOrNull() ?: return
        if (!_budget.value.canSubmit) return
        viewModelScope.launch {
            _budget.update { it.copy(isSubmitting = true) }
            when (val result = childRepository.setBudget(childId, amount)) {
                is AppResult.Success -> _budget.update { BudgetInputState() }
                is AppResult.Failure -> _budget.update {
                    it.copy(isSubmitting = false, error = result.error)
                }
            }
        }
    }
}
