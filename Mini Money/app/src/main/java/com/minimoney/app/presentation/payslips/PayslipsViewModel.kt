package com.minimoney.app.presentation.payslips

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.minimoney.app.domain.core.AppError
import com.minimoney.app.domain.core.AppResult
import com.minimoney.app.domain.payslip.Payslip
import com.minimoney.app.domain.payslip.PayslipRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class PayslipsViewModel @Inject constructor(
    private val payslipRepository: PayslipRepository,
    savedStateHandle: SavedStateHandle,
) : ViewModel() {

    val childId: Long = checkNotNull(savedStateHandle["childId"])

    val payslips: StateFlow<List<Payslip>> = payslipRepository.payslipsFor(childId)
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    private val _error = MutableStateFlow<AppError?>(null)
    val error: StateFlow<AppError?> = _error.asStateFlow()

    fun onGenerate() = viewModelScope.launch {
        _error.value = (payslipRepository.generate(childId) as? AppResult.Failure)?.error
    }

    /** "I have paid" — the payment itself happened outside the app. */
    fun onConfirmPaid(payslipId: Long) = viewModelScope.launch {
        _error.value = (payslipRepository.confirmPaid(payslipId) as? AppResult.Failure)?.error
    }

    /** One whole-Mbuck penalty step; the repository enforces the pilot/production cap. */
    fun onApplyPenaltyStep(payslipId: Long) = viewModelScope.launch {
        _error.value = (payslipRepository.applyLatePenalty(payslipId, 1) as? AppResult.Failure)?.error
    }
}
