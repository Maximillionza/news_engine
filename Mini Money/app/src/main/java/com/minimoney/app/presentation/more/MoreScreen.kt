package com.minimoney.app.presentation.more

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.minimoney.app.BuildConfig
import com.minimoney.app.R
import com.minimoney.app.domain.flags.FeatureFlags
import com.minimoney.app.ui.theme.CardShape
import com.minimoney.app.ui.theme.MiniMoneyTheme
import com.minimoney.app.ui.theme.TileShape
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import javax.inject.Inject

@HiltViewModel
class MoreViewModel @Inject constructor(featureFlags: FeatureFlags) : ViewModel() {
    val mpointsEnabled: StateFlow<Boolean> = featureFlags.mpointsEnabled
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), false)
    val accountLinkingEnabled: StateFlow<Boolean> = featureFlags.accountLinkingEnabled
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), false)
}

private enum class MoreTab { FAMILY, TOOLS, REWARDS }

private data class MoreTile(
    val labelRes: Int,
    val enabled: Boolean,
    val comingSoon: Boolean = false,
    val onClick: () -> Unit,
)

/**
 * More (handoff §Screens 10): secondary features in tabbed tile grid.
 * Mpoints/Account linking render dimmed with a "Coming soon" chip while their
 * regulatory flags are OFF — the flagged treatment is deliberate, don't
 * remove it without the flags actually being on.
 */
@Composable
fun MoreRoute(
    onOpenHome: () -> Unit,
    onOpenProfile: () -> Unit,
    onOpenExamBonus: () -> Unit,
    onOpenMpoints: () -> Unit,
    onOpenLinking: () -> Unit,
    viewModel: MoreViewModel = hiltViewModel(),
) {
    val colors = MiniMoneyTheme.colors
    val mpointsOn by viewModel.mpointsEnabled.collectAsStateWithLifecycle()
    val linkingOn by viewModel.accountLinkingEnabled.collectAsStateWithLifecycle()
    var tab by rememberSaveable { mutableStateOf(MoreTab.FAMILY) }

    val tiles = when (tab) {
        MoreTab.FAMILY -> listOf(
            MoreTile(R.string.parent_more_manage_children, enabled = true, onClick = onOpenHome),
            MoreTile(R.string.parent_more_add_child, enabled = true, onClick = onOpenHome),
            MoreTile(R.string.parent_more_profile, enabled = true, onClick = onOpenProfile),
        )
        MoreTab.TOOLS -> buildList {
            // Exam bonus stays gated to debug builds pre-specialist-review.
            if (BuildConfig.DEBUG) {
                add(MoreTile(R.string.parent_more_exam_bonus, enabled = true, onClick = onOpenExamBonus))
            }
            add(MoreTile(R.string.parent_more_disputes, enabled = true, onClick = onOpenHome))
            add(MoreTile(R.string.parent_more_late_penalty, enabled = true, onClick = onOpenHome))
        }
        MoreTab.REWARDS -> listOf(
            MoreTile(
                R.string.parent_more_mpoint_store,
                enabled = mpointsOn,
                comingSoon = !mpointsOn,
                onClick = onOpenMpoints,
            ),
            MoreTile(
                R.string.parent_more_account_linking,
                enabled = linkingOn,
                comingSoon = !linkingOn,
                onClick = onOpenLinking,
            ),
        )
    }

    Scaffold(containerColor = colors.background) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 20.dp),
        ) {
            Text(
                text = stringResource(R.string.parent_more_title),
                style = MaterialTheme.typography.headlineMedium,
                color = colors.text,
                fontWeight = FontWeight.ExtraBold,
                modifier = Modifier.padding(vertical = 16.dp),
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                FilterChip(
                    selected = tab == MoreTab.FAMILY,
                    onClick = { tab = MoreTab.FAMILY },
                    label = { Text(stringResource(R.string.parent_more_tab_family)) },
                )
                FilterChip(
                    selected = tab == MoreTab.TOOLS,
                    onClick = { tab = MoreTab.TOOLS },
                    label = { Text(stringResource(R.string.parent_more_tab_tools)) },
                )
                FilterChip(
                    selected = tab == MoreTab.REWARDS,
                    onClick = { tab = MoreTab.REWARDS },
                    label = { Text(stringResource(R.string.parent_more_tab_rewards)) },
                )
            }
            Row(
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                modifier = Modifier.padding(top = 16.dp),
            ) {
                tiles.forEach { tile ->
                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally,
                        modifier = Modifier
                            .weight(1f)
                            .alpha(if (tile.comingSoon) 0.55f else 1f)
                            .background(colors.surface, CardShape)
                            .clickable(enabled = tile.enabled, onClick = tile.onClick)
                            .padding(vertical = 18.dp),
                    ) {
                        Box(
                            Modifier
                                .size(44.dp)
                                .background(colors.surface2, TileShape),
                        )
                        Text(
                            text = stringResource(tile.labelRes),
                            color = colors.text,
                            fontSize = 11.5.sp,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.padding(top = 8.dp),
                        )
                        if (tile.comingSoon) {
                            Text(
                                text = stringResource(R.string.parent_more_coming_soon),
                                color = colors.accentText,
                                fontSize = 10.sp,
                            )
                        }
                    }
                }
            }
        }
    }
}
