package com.minimoney.app.presentation.tasks

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.minimoney.app.R
import com.minimoney.app.domain.dispute.Dispute
import com.minimoney.app.domain.dispute.DisputeStatus
import com.minimoney.app.domain.tasks.ChildTask
import com.minimoney.app.domain.tasks.EarnMode
import com.minimoney.app.domain.tasks.Frequency
import com.minimoney.app.domain.tasks.TaskStatus
import com.minimoney.app.domain.tasks.TaskTemplate

/** Parent-facing task management: creation, verification, dispute handling. */
@Composable
fun TasksRoute(viewModel: TasksViewModel = hiltViewModel()) {
    val tasks by viewModel.tasks.collectAsStateWithLifecycle()
    val disputes by viewModel.disputes.collectAsStateWithLifecycle()
    val createTask by viewModel.createTask.collectAsStateWithLifecycle()
    val child by viewModel.child.collectAsStateWithLifecycle()
    val templates by viewModel.templates.collectAsStateWithLifecycle()

    Scaffold { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp),
        ) {
            Text(
                text = stringResource(R.string.parent_tasks_title),
                style = MaterialTheme.typography.headlineMedium,
                modifier = Modifier.padding(vertical = 16.dp),
            )
            LazyColumn(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                if (tasks.isEmpty()) {
                    item { Text(stringResource(R.string.parent_tasks_empty)) }
                }
                items(tasks, key = { it.id }) { task ->
                    TaskCard(
                        task = task,
                        onVerify = { viewModel.onVerify(task.id) },
                        onDispute = { viewModel.onOpenDispute(task.id) },
                    )
                }
                val open = disputes.filter { it.status != DisputeStatus.ACCEPTED && it.status != DisputeStatus.DECLINED }
                if (open.isNotEmpty()) {
                    item {
                        Text(
                            text = stringResource(R.string.parent_disputes_title),
                            style = MaterialTheme.typography.titleMedium,
                            modifier = Modifier.padding(top = 16.dp),
                        )
                    }
                    items(open, key = { "d${it.id}" }) { dispute ->
                        DisputeCard(
                            dispute = dispute,
                            pastWindow = viewModel.isDisputePastWindow(dispute),
                            onAccept = { viewModel.onAcceptDispute(dispute.id) },
                            onDecline = { viewModel.onDeclineDispute(dispute.id) },
                            onEscalate = { viewModel.onEscalateDispute(dispute.id) },
                        )
                    }
                }
            }
            Button(
                onClick = viewModel::onShowCreateTask,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 16.dp),
            ) { Text(stringResource(R.string.parent_task_new)) }
        }
    }

    if (createTask.visible) {
        CreateTaskDialog(
            state = createTask,
            templates = templates,
            hasBudget = child?.budgetRand != null,
            onTemplateSelected = viewModel::onTemplateSelected,
            onTitleChanged = viewModel::onTitleChanged,
            onEarnModeChanged = viewModel::onEarnModeChanged,
            onValueChanged = viewModel::onValueInputChanged,
            onFrequencyChanged = viewModel::onFrequencyChanged,
            onSubmit = viewModel::onSubmitCreateTask,
            onDismiss = viewModel::onDismissCreateTask,
        )
    }
}

@Composable
private fun TaskCard(task: ChildTask, onVerify: () -> Unit, onDispute: () -> Unit) {
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(12.dp)) {
            Text(task.title, style = MaterialTheme.typography.titleMedium)
            Text(
                text = stringResource(R.string.parent_mbucks_format, task.mbuckValue) +
                    if (task.frequency != Frequency.MONTHLY) " · ${task.frequency.parentLabel()}" else "",
                style = MaterialTheme.typography.bodyMedium,
            )
            Text(task.status.parentLabel(), style = MaterialTheme.typography.bodySmall)
            if (task.status == TaskStatus.COMPLETED) {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    TextButton(onClick = onVerify) { Text(stringResource(R.string.parent_task_verify)) }
                    TextButton(onClick = onDispute) { Text(stringResource(R.string.parent_task_dispute)) }
                }
            }
        }
    }
}

@Composable
private fun DisputeCard(
    dispute: Dispute,
    pastWindow: Boolean,
    onAccept: () -> Unit,
    onDecline: () -> Unit,
    onEscalate: () -> Unit,
) {
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(12.dp)) {
            if (pastWindow && dispute.status == DisputeStatus.OPEN) {
                // Past-due banner + escalation path (BuildSpec §Screens/Flows 9).
                Text(
                    text = stringResource(R.string.parent_dispute_past_due),
                    color = MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.labelMedium,
                )
                TextButton(onClick = onEscalate) {
                    Text(stringResource(R.string.parent_dispute_escalate))
                }
            } else if (dispute.status == DisputeStatus.OPEN) {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    TextButton(onClick = onAccept) { Text(stringResource(R.string.parent_dispute_accept)) }
                    TextButton(onClick = onDecline) { Text(stringResource(R.string.parent_dispute_decline)) }
                }
            } else {
                Text(dispute.status.name, style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

@Composable
private fun CreateTaskDialog(
    state: CreateTaskState,
    templates: List<TaskTemplate>,
    hasBudget: Boolean,
    onTemplateSelected: (TaskTemplate?) -> Unit,
    onTitleChanged: (String) -> Unit,
    onEarnModeChanged: (EarnMode) -> Unit,
    onValueChanged: (String) -> Unit,
    onFrequencyChanged: (Frequency) -> Unit,
    onSubmit: () -> Unit,
    onDismiss: () -> Unit,
) {
    val isCustom = state.selectedTemplate == null
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.parent_task_new)) },
        text = {
            Column {
                Text(
                    text = stringResource(R.string.parent_task_pick_from_list),
                    style = MaterialTheme.typography.labelLarge,
                )
                Row(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    modifier = Modifier.padding(top = 8.dp),
                ) {
                    FilterChip(
                        selected = isCustom,
                        onClick = { onTemplateSelected(null) },
                        label = { Text(stringResource(R.string.parent_task_custom)) },
                    )
                }
                // Grouped by tier so a parent can see at a glance which chores
                // are daily/weekly/monthly, instead of one undifferentiated list.
                Frequency.entries.forEach { tier ->
                    val tierTemplates = templates.filter { it.tier == tier }
                    if (tierTemplates.isNotEmpty()) {
                        Text(
                            text = tier.parentLabel(),
                            style = MaterialTheme.typography.labelMedium,
                            modifier = Modifier.padding(top = 8.dp),
                        )
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            tierTemplates.forEach { template ->
                                FilterChip(
                                    selected = state.selectedTemplate == template,
                                    onClick = { onTemplateSelected(template) },
                                    label = { Text(template.title) },
                                )
                            }
                        }
                    }
                }
                OutlinedTextField(
                    value = state.title,
                    onValueChange = onTitleChanged,
                    label = { Text(stringResource(R.string.parent_task_title_label)) },
                    // Renaming is purely cosmetic — it doesn't affect the reward
                    // calculation, so it's always editable, preset or not.
                    modifier = Modifier.padding(top = 12.dp),
                    singleLine = true,
                )
                // Per-task earn-mode + value entry — only meaningful for custom
                // tasks; a preset's reward is fixed by its tier and weight, so
                // showing a disabled numeric field here would look broken rather
                // than intentional. Show what it means in plain words instead.
                if (isCustom) {
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        modifier = Modifier.padding(vertical = 12.dp),
                    ) {
                        FilterChip(
                            selected = state.earnMode == EarnMode.FIXED,
                            onClick = { onEarnModeChanged(EarnMode.FIXED) },
                            label = { Text(stringResource(R.string.parent_task_mode_fixed)) },
                        )
                        FilterChip(
                            selected = state.earnMode == EarnMode.PERCENTAGE,
                            onClick = { onEarnModeChanged(EarnMode.PERCENTAGE) },
                            label = { Text(stringResource(R.string.parent_task_mode_percentage)) },
                        )
                    }
                    OutlinedTextField(
                        value = state.valueInput,
                        onValueChange = onValueChanged,
                        label = {
                            Text(
                                stringResource(
                                    if (state.earnMode == EarnMode.FIXED) R.string.parent_task_value_fixed_label
                                    else R.string.parent_task_value_percent_label,
                                ),
                            )
                        },
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                        singleLine = true,
                    )
                    Text(
                        text = stringResource(R.string.parent_task_frequency_label),
                        style = MaterialTheme.typography.labelLarge,
                        modifier = Modifier.padding(top = 12.dp),
                    )
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        modifier = Modifier.padding(vertical = 8.dp),
                    ) {
                        Frequency.entries.forEach { freq ->
                            FilterChip(
                                selected = state.frequency == freq,
                                onClick = { onFrequencyChanged(freq) },
                                label = { Text(freq.parentLabel()) },
                            )
                        }
                    }
                } else {
                    Text(
                        text = stringResource(R.string.parent_task_tier_locked_note, state.frequency.parentLabel()),
                        style = MaterialTheme.typography.bodySmall,
                        modifier = Modifier.padding(top = 12.dp),
                    )
                }
                val preview = state.previewMbucks
                Text(
                    text = when {
                        state.earnMode != EarnMode.FIXED && !hasBudget ->
                            stringResource(R.string.parent_task_percent_needs_budget)
                        preview != null -> stringResource(R.string.parent_task_percent_preview, preview)
                        else -> ""
                    },
                    style = MaterialTheme.typography.bodySmall,
                    modifier = Modifier.padding(top = 8.dp),
                )
            }
        },
        confirmButton = {
            TextButton(onClick = onSubmit, enabled = state.canSubmit) {
                Text(stringResource(R.string.parent_task_save))
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text(stringResource(R.string.parent_add_child_cancel))
            }
        },
    )
}

@Composable
private fun Frequency.parentLabel(): String = when (this) {
    Frequency.DAILY -> stringResource(R.string.parent_task_frequency_daily)
    Frequency.WEEKLY -> stringResource(R.string.parent_task_frequency_weekly)
    Frequency.MONTHLY -> stringResource(R.string.parent_task_frequency_monthly)
}

@Composable
private fun TaskStatus.parentLabel(): String = when (this) {
    TaskStatus.ASSIGNED -> stringResource(R.string.parent_task_status_assigned)
    TaskStatus.COMPLETED -> stringResource(R.string.parent_task_status_completed)
    TaskStatus.VERIFIED -> stringResource(R.string.parent_task_status_verified)
    TaskStatus.DISPUTED -> stringResource(R.string.parent_task_status_disputed)
}
