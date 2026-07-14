package com.minimoney.app.presentation.home

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
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
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.minimoney.app.R
import com.minimoney.app.domain.child.AgeBand
import com.minimoney.app.domain.child.ChildProfile
import com.minimoney.app.domain.core.AppError

@Composable
fun HomeRoute(
    onOpenChild: (Long) -> Unit,
    onOpenAccountLinking: () -> Unit,
    viewModel: HomeViewModel = hiltViewModel(),
) {
    val children by viewModel.children.collectAsStateWithLifecycle()
    val addChild by viewModel.addChild.collectAsStateWithLifecycle()
    val linkingEnabled by viewModel.accountLinkingEnabled.collectAsStateWithLifecycle()

    Scaffold { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp),
        ) {
            Text(
                text = stringResource(R.string.parent_home_title),
                style = MaterialTheme.typography.headlineMedium,
                modifier = Modifier.padding(vertical = 16.dp),
            )
            if (children.isEmpty()) {
                Text(
                    text = stringResource(R.string.parent_home_empty),
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
            LazyColumn(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(children, key = { it.id }) { child ->
                    ChildRow(child = child, onClick = { onOpenChild(child.id) })
                }
            }
            Button(
                onClick = viewModel::onShowAddChild,
                enabled = children.size < 4,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 16.dp),
            ) { Text(stringResource(R.string.parent_home_add_child)) }
            if (linkingEnabled) {
                TextButton(
                    onClick = onOpenAccountLinking,
                    modifier = Modifier.fillMaxWidth(),
                ) { Text(stringResource(R.string.parent_home_account_linking)) }
            }
        }
    }

    if (addChild.visible) {
        AddChildDialog(
            state = addChild,
            onNameChanged = viewModel::onNameChanged,
            onAgeBandSelected = viewModel::onAgeBandSelected,
            onSubmit = viewModel::onSubmitAddChild,
            onDismiss = viewModel::onDismissAddChild,
        )
    }
}

@Composable
private fun ChildRow(child: ChildProfile, onClick: () -> Unit) {
    Card(modifier = Modifier
        .fillMaxWidth()
        .clickable(onClick = onClick)) {
        Column(Modifier.padding(16.dp)) {
            Text(child.displayName, style = MaterialTheme.typography.titleMedium)
            Text(
                text = child.ageBand.label(),
                style = MaterialTheme.typography.bodySmall,
            )
        }
    }
}

@Composable
private fun AddChildDialog(
    state: AddChildState,
    onNameChanged: (String) -> Unit,
    onAgeBandSelected: (AgeBand) -> Unit,
    onSubmit: () -> Unit,
    onDismiss: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.parent_add_child_title)) },
        text = {
            Column {
                OutlinedTextField(
                    value = state.name,
                    onValueChange = onNameChanged,
                    label = { Text(stringResource(R.string.parent_add_child_name)) },
                    singleLine = true,
                )
                Text(
                    text = stringResource(R.string.parent_add_child_age_band),
                    style = MaterialTheme.typography.labelMedium,
                    modifier = Modifier.padding(top = 12.dp, bottom = 4.dp),
                )
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    AgeBand.entries.forEach { band ->
                        FilterChip(
                            selected = state.ageBand == band,
                            onClick = { onAgeBandSelected(band) },
                            label = { Text(band.label()) },
                        )
                    }
                }
                if (state.error == AppError.Conflict) {
                    Text(
                        text = stringResource(R.string.parent_add_child_limit),
                        color = MaterialTheme.colorScheme.error,
                        style = MaterialTheme.typography.bodySmall,
                        modifier = Modifier.padding(top = 8.dp),
                    )
                }
            }
        },
        confirmButton = {
            TextButton(onClick = onSubmit, enabled = state.canSubmit) {
                Text(stringResource(R.string.parent_add_child_save))
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
fun AgeBand.label(): String = when (this) {
    AgeBand.SIX_TO_NINE -> stringResource(R.string.parent_age_band_6_9)
    AgeBand.TEN_TO_FOURTEEN -> stringResource(R.string.parent_age_band_10_14)
    AgeBand.FIFTEEN_TO_EIGHTEEN -> stringResource(R.string.parent_age_band_15_18)
}
