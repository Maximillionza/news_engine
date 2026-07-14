package com.minimoney.app.presentation.child

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
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
import com.minimoney.app.presentation.home.label

@Composable
fun ChildDetailRoute(
    onOpenTasks: (Long) -> Unit,
    onOpenPayslips: (Long) -> Unit,
    onOpenChildView: (Long) -> Unit,
    viewModel: ChildDetailViewModel = hiltViewModel(),
) {
    val child by viewModel.child.collectAsStateWithLifecycle()
    val budget by viewModel.budget.collectAsStateWithLifecycle()
    val current = child ?: return

    Scaffold { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(
                text = current.displayName,
                style = MaterialTheme.typography.headlineMedium,
                modifier = Modifier.padding(top = 16.dp),
            )
            Text(current.ageBand.label(), style = MaterialTheme.typography.bodyMedium)

            Text(
                text = stringResource(R.string.parent_budget_title),
                style = MaterialTheme.typography.titleMedium,
                modifier = Modifier.padding(top = 8.dp),
            )
            Text(
                text = current.budgetRand?.let { stringResource(R.string.parent_budget_current, it) }
                    ?: stringResource(R.string.parent_budget_none),
                style = MaterialTheme.typography.bodyMedium,
            )
            // Whole-Rand only: the ViewModel ignores any edit containing a
            // non-digit, so a decimal point cannot even appear in this field.
            OutlinedTextField(
                value = budget.input,
                onValueChange = viewModel::onBudgetInputChanged,
                label = { Text(stringResource(R.string.parent_budget_label)) },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
            Button(
                onClick = viewModel::onSubmitBudget,
                enabled = budget.canSubmit,
                modifier = Modifier.fillMaxWidth(),
            ) { Text(stringResource(R.string.parent_budget_save)) }

            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = { onOpenTasks(current.id) }) {
                    Text(stringResource(R.string.parent_open_tasks))
                }
                OutlinedButton(onClick = { onOpenPayslips(current.id) }) {
                    Text(stringResource(R.string.parent_open_payslips))
                }
            }
            TextButton(onClick = { onOpenChildView(current.id) }) {
                Text(stringResource(R.string.parent_open_child_view))
            }
        }
    }
}
