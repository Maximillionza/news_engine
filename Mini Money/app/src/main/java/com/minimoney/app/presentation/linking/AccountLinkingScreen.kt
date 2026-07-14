package com.minimoney.app.presentation.linking

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.minimoney.app.R

/**
 * Account-linking stub — reachable only while ACCOUNT_LINKING_ENABLED is on
 * (OFF at launch pending the SARB/NPS Act recheck). Deliberately contains NO
 * aggregator SDK integration: BuildSpec §Third-Party Dependencies forbids
 * finalizing any SDK contract/cost commitment until that recheck resolves.
 * When linking goes live, the confirmed-payment signal from here is what
 * permits the ZAR display substitution (display-layer only, never the ledger).
 */
@Composable
fun AccountLinkingRoute() {
    Scaffold { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp),
        ) {
            Text(
                text = stringResource(R.string.parent_linking_title),
                style = MaterialTheme.typography.headlineMedium,
            )
            Text(
                text = stringResource(R.string.parent_linking_pending),
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.padding(top = 12.dp),
            )
        }
    }
}
