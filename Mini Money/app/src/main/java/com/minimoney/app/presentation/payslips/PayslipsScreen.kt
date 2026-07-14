package com.minimoney.app.presentation.payslips

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
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.minimoney.app.R
import com.minimoney.app.domain.payslip.Payslip
import com.minimoney.app.domain.payslip.PayslipStatus

/** Parent-facing: the invoice/payslip surface. Amounts are Mbucks, always. */
@Composable
fun PayslipsRoute(viewModel: PayslipsViewModel = hiltViewModel()) {
    val payslips by viewModel.payslips.collectAsStateWithLifecycle()

    Scaffold { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp),
        ) {
            Text(
                text = stringResource(R.string.parent_payslips_title),
                style = MaterialTheme.typography.headlineMedium,
                modifier = Modifier.padding(vertical = 16.dp),
            )
            LazyColumn(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                if (payslips.isEmpty()) {
                    item { Text(stringResource(R.string.parent_payslips_empty)) }
                }
                items(payslips, key = { it.id }) { payslip ->
                    PayslipCard(
                        payslip = payslip,
                        onConfirmPaid = { viewModel.onConfirmPaid(payslip.id) },
                        onApplyPenalty = { viewModel.onApplyPenaltyStep(payslip.id) },
                    )
                }
            }
            Button(
                onClick = viewModel::onGenerate,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 16.dp),
            ) { Text(stringResource(R.string.parent_payslip_generate)) }
        }
    }
}

@Composable
private fun PayslipCard(
    payslip: Payslip,
    onConfirmPaid: () -> Unit,
    onApplyPenalty: () -> Unit,
) {
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(12.dp)) {
            Text(
                text = stringResource(R.string.parent_payslip_earned, payslip.earnedMbucks),
                style = MaterialTheme.typography.bodyMedium,
            )
            if (payslip.penaltyMbucks > 0) {
                Text(
                    text = stringResource(R.string.parent_payslip_penalty, payslip.penaltyMbucks),
                    color = MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
            Text(
                text = stringResource(R.string.parent_payslip_total, payslip.totalOwedMbucks),
                style = MaterialTheme.typography.titleMedium,
            )
            Text(
                text = stringResource(
                    if (payslip.status == PayslipStatus.PAID) R.string.parent_payslip_status_paid
                    else R.string.parent_payslip_status_generated,
                ),
                style = MaterialTheme.typography.bodySmall,
            )
            if (payslip.status == PayslipStatus.GENERATED) {
                Text(
                    text = stringResource(R.string.parent_payslip_confirm_paid_note),
                    style = MaterialTheme.typography.bodySmall,
                    modifier = Modifier.padding(top = 4.dp),
                )
                Button(onClick = onConfirmPaid, modifier = Modifier.padding(top = 8.dp)) {
                    Text(stringResource(R.string.parent_payslip_confirm_paid))
                }
                TextButton(onClick = onApplyPenalty) {
                    Text(stringResource(R.string.parent_payslip_apply_penalty))
                }
            }
        }
    }
}
