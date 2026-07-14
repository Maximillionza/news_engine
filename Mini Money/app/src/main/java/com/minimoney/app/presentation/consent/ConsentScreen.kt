package com.minimoney.app.presentation.consent

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.minimoney.app.R
import com.minimoney.app.domain.consent.ConsentSection
import com.minimoney.app.domain.core.AppError

/**
 * POPIA consent flow — parent-facing surface, structurally separate from
 * registration (BuildSpec §Screens/Flows 3). No navigation callbacks: routing
 * in and out of this screen is owned entirely by the session-driven root.
 */
@Composable
fun ConsentRoute(viewModel: ConsentViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()
    ConsentScreen(
        state = state,
        onAckToggled = viewModel::onAckToggled,
        onAccept = viewModel::onAccept,
        onDecline = viewModel::onDecline,
        onRetry = viewModel::onRetry,
    )
}

@Composable
fun ConsentScreen(
    state: ConsentUiState,
    onAckToggled: (Boolean) -> Unit,
    onAccept: () -> Unit,
    onDecline: () -> Unit,
    onRetry: () -> Unit,
) {
    Scaffold { padding ->
        when {
            state.isLoading -> Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding),
                contentAlignment = Alignment.Center,
            ) { CircularProgressIndicator() }

            state.loadError != null -> LoadErrorContent(
                error = state.loadError,
                onRetry = onRetry,
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding),
            )

            state.document != null -> ConsentContent(
                sections = state.document.sections,
                ackChecked = state.ackChecked,
                canAccept = state.canAccept,
                isSubmitting = state.isSubmitting,
                submitError = state.submitError,
                onAckToggled = onAckToggled,
                onAccept = onAccept,
                onDecline = onDecline,
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .padding(horizontal = 24.dp),
            )
        }
    }
}

@Composable
private fun ConsentContent(
    sections: List<ConsentSection>,
    ackChecked: Boolean,
    canAccept: Boolean,
    isSubmitting: Boolean,
    submitError: AppError?,
    onAckToggled: (Boolean) -> Unit,
    onAccept: () -> Unit,
    onDecline: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(modifier = modifier) {
        Text(
            text = stringResource(R.string.parent_consent_title),
            style = MaterialTheme.typography.headlineMedium,
            modifier = Modifier.padding(top = 16.dp, bottom = 8.dp),
        )
        // The document scrolls; the acknowledgement and actions stay pinned
        // below it so accepting always happens with the controls visible.
        LazyColumn(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            items(sections, key = { it.title }) { section ->
                Column {
                    Text(section.title, style = MaterialTheme.typography.titleMedium)
                    Text(
                        section.body,
                        style = MaterialTheme.typography.bodyMedium,
                        modifier = Modifier.padding(top = 4.dp),
                    )
                }
            }
        }
        Row(verticalAlignment = Alignment.CenterVertically) {
            Checkbox(
                checked = ackChecked,
                onCheckedChange = onAckToggled,
                enabled = !isSubmitting,
            )
            Text(
                text = stringResource(R.string.parent_consent_ack),
                style = MaterialTheme.typography.bodySmall,
            )
        }
        if (submitError != null) {
            Text(
                text = stringResource(submitError.messageRes()),
                color = MaterialTheme.colorScheme.error,
                style = MaterialTheme.typography.bodySmall,
            )
        }
        Button(
            onClick = onAccept,
            enabled = canAccept,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 8.dp),
        ) {
            if (isSubmitting) {
                CircularProgressIndicator(
                    modifier = Modifier.padding(vertical = 2.dp),
                    strokeWidth = 2.dp,
                )
            } else {
                Text(stringResource(R.string.parent_consent_accept))
            }
        }
        TextButton(
            onClick = onDecline,
            enabled = !isSubmitting,
            modifier = Modifier
                .fillMaxWidth()
                .padding(bottom = 8.dp),
        ) {
            Text(stringResource(R.string.parent_consent_decline))
        }
    }
}

@Composable
private fun LoadErrorContent(
    error: AppError,
    onRetry: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier,
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            text = stringResource(error.messageRes()),
            color = MaterialTheme.colorScheme.error,
            style = MaterialTheme.typography.bodyMedium,
        )
        TextButton(onClick = onRetry) {
            Text(stringResource(R.string.parent_consent_retry))
        }
    }
}

private fun AppError.messageRes(): Int = when (this) {
    AppError.Network -> R.string.parent_error_network
    AppError.Conflict -> R.string.parent_consent_version_changed
    is AppError.Server -> R.string.parent_error_server
    is AppError.Unknown -> R.string.parent_error_unknown
}
