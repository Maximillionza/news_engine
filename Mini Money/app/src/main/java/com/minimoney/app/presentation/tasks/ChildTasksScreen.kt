package com.minimoney.app.presentation.tasks

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.minimoney.app.R
import com.minimoney.app.domain.tasks.ChildTask
import com.minimoney.app.domain.tasks.TaskStatus

/**
 * CHILD-FACING surface. Every string here MUST come from strings_child.xml —
 * the childFacingTermLint build task enforces the no-debt-language rule on
 * that file (BuildSpec §Compliance: terminology governance). No payslip,
 * penalty, or dispute concepts are rendered on this screen at all.
 */
@Composable
fun ChildTasksRoute(viewModel: ChildTasksViewModel = hiltViewModel()) {
    val tasks by viewModel.tasks.collectAsStateWithLifecycle()

    Scaffold { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp),
        ) {
            Text(
                text = stringResource(R.string.child_tasks_title),
                style = MaterialTheme.typography.headlineMedium,
                modifier = Modifier.padding(vertical = 16.dp),
            )
            if (tasks.isEmpty()) {
                Text(stringResource(R.string.child_tasks_empty))
            }
            LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                items(tasks, key = { it.id }) { task ->
                    ChildTaskCard(task = task, onMarkDone = { viewModel.onMarkDone(task.id) })
                }
            }
        }
    }
}

@Composable
private fun ChildTaskCard(task: ChildTask, onMarkDone: () -> Unit) {
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(12.dp)) {
            Text(task.title, style = MaterialTheme.typography.titleMedium)
            Text(
                text = stringResource(R.string.child_task_reward, task.mbuckValue),
                style = MaterialTheme.typography.bodyMedium,
            )
            when (task.status) {
                TaskStatus.ASSIGNED -> Button(
                    onClick = onMarkDone,
                    modifier = Modifier.padding(top = 8.dp),
                ) { Text(stringResource(R.string.child_task_mark_done)) }
                TaskStatus.COMPLETED -> Text(
                    text = stringResource(R.string.child_task_waiting_check),
                    style = MaterialTheme.typography.bodySmall,
                )
                TaskStatus.VERIFIED -> Text(
                    text = stringResource(R.string.child_task_done),
                    style = MaterialTheme.typography.bodySmall,
                )
                TaskStatus.DISPUTED -> Text(
                    // Softened: the child never sees dispute/debt framing.
                    text = stringResource(R.string.child_task_being_looked_at),
                    style = MaterialTheme.typography.bodySmall,
                )
            }
        }
    }
}
