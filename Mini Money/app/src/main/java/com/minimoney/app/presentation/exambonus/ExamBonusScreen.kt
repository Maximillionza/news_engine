package com.minimoney.app.presentation.exambonus

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.minimoney.app.R
import com.minimoney.app.data.db.ExamBonusDao
import com.minimoney.app.data.db.ExamBonusRecordEntity
import com.minimoney.app.domain.core.Clock
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

/**
 * Exam-bonus hybrid input (BuildSpec §Build-Spec Items Introduced by the
 * Hybrid Bonus): behavior checklist primary, self-reported grade secondary.
 * NO Mbuck bonus is calculated or written anywhere — the bonus-value mechanism
 * is deliberately unspecified pending founder confirmation, and if it becomes
 * percentage-based it must apply the truncation rule.
 *
 * GATE: this route is only reachable in debug builds (see ParentNavGraph) —
 * build/QA with test data only, until the child-development specialist's
 * motivation-probe review has documented sign-off.
 */
data class ExamBonusState(
    val behaviors: Map<Int, Boolean> = emptyMap(),
    val grade: String = "",
    val saved: Boolean = false,
)

@HiltViewModel
class ExamBonusViewModel @Inject constructor(
    private val examBonusDao: ExamBonusDao,
    private val clock: Clock,
    savedStateHandle: SavedStateHandle,
) : ViewModel() {

    val childId: Long = checkNotNull(savedStateHandle["childId"])

    private val _state = MutableStateFlow(ExamBonusState())
    val state: StateFlow<ExamBonusState> = _state.asStateFlow()

    fun onBehaviorToggled(index: Int, checked: Boolean) =
        _state.update { it.copy(behaviors = it.behaviors + (index to checked), saved = false) }

    fun onGradeChanged(value: String) = _state.update { it.copy(grade = value, saved = false) }

    fun onSave() {
        val snapshot = _state.value
        viewModelScope.launch {
            examBonusDao.insert(
                ExamBonusRecordEntity(
                    childId = childId,
                    behaviorChecklistJson = snapshot.behaviors
                        .filterValues { it }.keys.sorted().joinToString(",", "[", "]"),
                    gradeInput = snapshot.grade.ifBlank { null },
                    recordedAtMillis = clock.nowMillis(),
                ),
            )
            _state.update { it.copy(saved = true) }
        }
    }
}

@Composable
fun ExamBonusRoute(viewModel: ExamBonusViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val behaviorLabels = listOf(
        R.string.parent_exam_bonus_behavior_1,
        R.string.parent_exam_bonus_behavior_2,
        R.string.parent_exam_bonus_behavior_3,
    )

    Scaffold { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp),
        ) {
            Text(
                text = stringResource(R.string.parent_exam_bonus_title),
                style = MaterialTheme.typography.headlineMedium,
                modifier = Modifier.padding(vertical = 16.dp),
            )
            Text(
                text = stringResource(R.string.parent_exam_bonus_gate_note),
                color = MaterialTheme.colorScheme.error,
                style = MaterialTheme.typography.bodySmall,
            )
            behaviorLabels.forEachIndexed { index, labelRes ->
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Checkbox(
                        checked = state.behaviors[index] == true,
                        onCheckedChange = { viewModel.onBehaviorToggled(index, it) },
                    )
                    Text(stringResource(labelRes), style = MaterialTheme.typography.bodyMedium)
                }
            }
            OutlinedTextField(
                value = state.grade,
                onValueChange = viewModel::onGradeChanged,
                label = { Text(stringResource(R.string.parent_exam_bonus_grade_label)) },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
            Button(
                onClick = viewModel::onSave,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 16.dp),
            ) { Text(stringResource(R.string.parent_exam_bonus_save)) }
            if (state.saved) Text("✓", modifier = Modifier.padding(top = 8.dp))
        }
    }
}
