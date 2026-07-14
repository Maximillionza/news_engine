package com.minimoney.app.presentation.home

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.minimoney.app.domain.child.AgeBand
import com.minimoney.app.domain.child.ChildProfile
import com.minimoney.app.domain.child.ChildRepository
import com.minimoney.app.domain.child.MAX_CHILDREN_PER_PARENT
import com.minimoney.app.domain.core.AppError
import com.minimoney.app.domain.core.AppResult
import com.minimoney.app.domain.flags.FeatureFlags
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class AddChildState(
    val visible: Boolean = false,
    val name: String = "",
    val ageBand: AgeBand? = null,
    val isSubmitting: Boolean = false,
    val error: AppError? = null,
) {
    val canSubmit: Boolean get() = name.isNotBlank() && ageBand != null && !isSubmitting
}

@HiltViewModel
class HomeViewModel @Inject constructor(
    private val childRepository: ChildRepository,
    featureFlags: FeatureFlags,
) : ViewModel() {

    val children: StateFlow<List<ChildProfile>> = childRepository.children()
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

    fun onSubmitAddChild() {
        val state = _addChild.value
        val band = state.ageBand ?: return
        if (!state.canSubmit) return
        viewModelScope.launch {
            _addChild.update { it.copy(isSubmitting = true) }
            when (val result = childRepository.createChild(state.name, band)) {
                is AppResult.Success -> _addChild.update { AddChildState() }
                is AppResult.Failure -> _addChild.update {
                    it.copy(isSubmitting = false, error = result.error)
                }
            }
        }
    }
}
