package com.minimoney.app.presentation.mpoints

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.minimoney.app.R
import com.minimoney.app.data.db.LedgerDao
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import javax.inject.Inject

/**
 * Mpoint balance + store placeholder — reachable only while MPOINTS_ENABLED
 * is on (OFF at launch pending the FPB recheck); the nav entry is hidden
 * otherwise. The cosmetic store itself is a v-next surface behind the same flag.
 */
@HiltViewModel
class MpointsViewModel @Inject constructor(
    ledgerDao: LedgerDao,
    savedStateHandle: SavedStateHandle,
) : ViewModel() {
    val childId: Long = checkNotNull(savedStateHandle["childId"])

    val balance: StateFlow<Int> = ledgerDao.totalMpointsFor(childId)
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), 0)
}

@Composable
fun MpointsRoute(viewModel: MpointsViewModel = hiltViewModel()) {
    val balance by viewModel.balance.collectAsStateWithLifecycle()
    Scaffold { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp),
        ) {
            Text(
                text = stringResource(R.string.parent_mpoints_title),
                style = MaterialTheme.typography.headlineMedium,
            )
            Text(
                text = stringResource(R.string.parent_mpoints_balance, balance),
                style = MaterialTheme.typography.bodyLarge,
                modifier = Modifier.padding(top = 8.dp),
            )
            Text(
                text = stringResource(R.string.parent_mpoints_store_pending),
                style = MaterialTheme.typography.bodySmall,
                modifier = Modifier.padding(top = 16.dp),
            )
        }
    }
}
