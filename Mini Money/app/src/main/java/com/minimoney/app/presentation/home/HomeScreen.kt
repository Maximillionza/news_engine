package com.minimoney.app.presentation.home

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.minimoney.app.R
import com.minimoney.app.domain.child.AgeBand
import com.minimoney.app.domain.child.ChildProfile
import com.minimoney.app.domain.core.AppError
import com.minimoney.app.ui.theme.HeroCardShape
import com.minimoney.app.ui.theme.MiniMoneyTheme
import com.minimoney.app.ui.theme.PillShape
import com.minimoney.app.ui.theme.RowShape
import com.minimoney.app.ui.theme.childGradient

@Composable
fun HomeRoute(
    onOpenChild: (Long) -> Unit,
    onOpenTasks: (Long) -> Unit,
    onOpenPayslips: (Long) -> Unit,
    onOpenAccountLinking: () -> Unit,
    onOpenMore: () -> Unit,
    onOpenProfile: () -> Unit,
    viewModel: HomeViewModel = hiltViewModel(),
) {
    val children by viewModel.children.collectAsStateWithLifecycle()
    val addChild by viewModel.addChild.collectAsStateWithLifecycle()
    val linkingEnabled by viewModel.accountLinkingEnabled.collectAsStateWithLifecycle()
    val selectedChildId by viewModel.selectedChildId.collectAsStateWithLifecycle()
    val monthToDate by viewModel.monthToDate.collectAsStateWithLifecycle()
    val pendingVerify by viewModel.pendingVerify.collectAsStateWithLifecycle()
    val selectedTasks by viewModel.selectedChildTasks.collectAsStateWithLifecycle()
    val colors = MiniMoneyTheme.colors

    Scaffold(containerColor = colors.background) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 20.dp),
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.padding(vertical = 16.dp),
            ) {
                Text(
                    text = stringResource(R.string.parent_home_title),
                    style = MaterialTheme.typography.headlineMedium,
                    color = colors.text,
                    fontWeight = FontWeight.ExtraBold,
                    modifier = Modifier.weight(1f),
                )
                TextButton(onClick = onOpenMore) {
                    Text(stringResource(R.string.parent_home_more), color = colors.textMuted)
                }
                // Avatar-initial button (handoff top bar) → Profile.
                Box(
                    modifier = Modifier
                        .size(36.dp)
                        .background(colors.accentGradient, CircleShape)
                        .clickable(onClick = onOpenProfile),
                    contentAlignment = Alignment.Center,
                ) {
                    Text("M", color = Color.White, fontWeight = FontWeight.ExtraBold)
                }
            }
            // Family / per-child chip row (handoff §Screens 4): switches this
            // same screen between the Family overview and one child's view.
            Row(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier
                    .horizontalScroll(rememberScrollState())
                    .padding(bottom = 12.dp),
            ) {
                FilterChip(
                    selected = selectedChildId == null,
                    onClick = { viewModel.onChildChipSelected(null) },
                    label = { Text(stringResource(R.string.parent_home_family_chip)) },
                )
                children.forEach { child ->
                    FilterChip(
                        selected = selectedChildId == child.id,
                        onClick = { viewModel.onChildChipSelected(child.id) },
                        label = { Text(child.displayName) },
                    )
                }
            }
            if (children.isEmpty()) {
                Text(
                    text = stringResource(R.string.parent_home_empty),
                    style = MaterialTheme.typography.bodyMedium,
                    color = colors.textMuted,
                )
            }
            val selected = children.firstOrNull { it.id == selectedChildId }
            LazyColumn(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                if (selected == null) {
                    items(children, key = { it.id }) { child ->
                        FamilyChildCard(
                            child = child,
                            monthToDate = monthToDate[child.id] ?: 0,
                            pendingCount = pendingVerify[child.id] ?: 0,
                            onOpenProfile = { onOpenChild(child.id) },
                            onManage = { onOpenTasks(child.id) },
                            onVerify = { onOpenTasks(child.id) },
                        )
                    }
                } else {
                    item(key = "hero") {
                        SingleChildHero(
                            child = selected,
                            monthToDate = monthToDate[selected.id] ?: 0,
                            onMyTasks = { onOpenTasks(selected.id) },
                            onPayslip = { onOpenPayslips(selected.id) },
                            onOpenProfile = { onOpenChild(selected.id) },
                        )
                    }
                    item(key = "week-label") {
                        Text(
                            text = stringResource(R.string.parent_home_week_tasks),
                            style = MaterialTheme.typography.titleMedium,
                            color = colors.text,
                            modifier = Modifier.padding(top = 8.dp),
                        )
                    }
                    items(selectedTasks, key = { "t${it.id}" }) { task ->
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            modifier = Modifier
                                .fillMaxWidth()
                                .background(colors.surface, RowShape)
                                .padding(horizontal = 16.dp, vertical = 14.dp),
                        ) {
                            Column(Modifier.weight(1f)) {
                                Text(task.title, color = colors.text, fontWeight = FontWeight.SemiBold)
                                Text(task.status, color = colors.textMuted, fontSize = 12.sp)
                            }
                            Text(
                                text = stringResource(R.string.parent_home_task_mbucks, task.mbuckValue),
                                color = colors.accentText,
                                fontWeight = FontWeight.Bold,
                            )
                        }
                    }
                }
            }
            Button(
                onClick = viewModel::onShowAddChild,
                enabled = children.size < 4,
                shape = PillShape,
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
            onChildEmailChanged = viewModel::onChildEmailChanged,
            onSubmit = viewModel::onSubmitAddChild,
            onDismiss = viewModel::onDismissAddChild,
        )
    }
}

@Composable
private fun ChildAvatar(name: String, size: androidx.compose.ui.unit.Dp) {
    Box(
        modifier = Modifier
            .size(size)
            .background(Color.White.copy(alpha = 0.25f), CircleShape),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = name.take(1).uppercase(),
            color = Color.White,
            fontWeight = FontWeight.ExtraBold,
        )
    }
}

/** Family-view card (handoff §Screens 4): child gradient, month-to-date, Manage/Verify. */
@Composable
private fun FamilyChildCard(
    child: ChildProfile,
    monthToDate: Int,
    pendingCount: Int,
    onOpenProfile: () -> Unit,
    onManage: () -> Unit,
    onVerify: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(childGradient(child.id), HeroCardShape)
            .clickable(onClick = onOpenProfile)
            .padding(20.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            ChildAvatar(child.displayName, 38.dp)
            Column(
                Modifier
                    .weight(1f)
                    .padding(start = 10.dp),
            ) {
                Text(child.displayName, color = Color.White, fontSize = 15.sp, fontWeight = FontWeight.ExtraBold)
                Text(child.ageBand.label(), color = Color.White.copy(alpha = 0.85f), fontSize = 11.sp)
            }
            if (pendingCount > 0) {
                Text(
                    text = stringResource(R.string.parent_home_to_verify, pendingCount),
                    color = Color.White,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier
                        .background(Color.Black.copy(alpha = 0.28f), PillShape)
                        .padding(horizontal = 10.dp, vertical = 4.dp),
                )
            }
        }
        Text(
            text = stringResource(R.string.parent_home_month_to_date).uppercase(),
            color = Color.White.copy(alpha = 0.8f),
            fontSize = 11.sp,
            modifier = Modifier.padding(top = 16.dp),
        )
        Text(
            text = stringResource(R.string.parent_home_mbuck_total, monthToDate),
            color = Color.White,
            fontSize = 32.sp,
            fontWeight = FontWeight.ExtraBold,
        )
        Row(
            horizontalArrangement = Arrangement.spacedBy(10.dp),
            modifier = Modifier.padding(top = 14.dp),
        ) {
            Button(
                onClick = onManage,
                shape = PillShape,
                colors = ButtonDefaults.buttonColors(containerColor = Color.White, contentColor = Color(0xFF161B2E)),
                contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 24.dp, vertical = 12.dp),
            ) { Text(stringResource(R.string.parent_home_manage), fontWeight = FontWeight.Bold) }
            OutlinedButton(
                onClick = onVerify,
                shape = PillShape,
                colors = ButtonDefaults.outlinedButtonColors(contentColor = Color.White),
                contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 24.dp, vertical = 12.dp),
            ) { Text(stringResource(R.string.parent_home_verify), fontWeight = FontWeight.Bold) }
        }
    }
}

/** Single-child hero (handoff §Screens 5). */
@Composable
private fun SingleChildHero(
    child: ChildProfile,
    monthToDate: Int,
    onMyTasks: () -> Unit,
    onPayslip: () -> Unit,
    onOpenProfile: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(childGradient(child.id), HeroCardShape)
            .clickable(onClick = onOpenProfile)
            .padding(20.dp),
    ) {
        Text(
            text = stringResource(R.string.parent_home_hero_kicker, child.displayName),
            color = Color.White.copy(alpha = 0.85f),
            fontSize = 12.sp,
        )
        Text(
            text = stringResource(R.string.parent_home_mbuck_total, monthToDate),
            color = Color.White,
            fontSize = 40.sp,
            fontWeight = FontWeight.ExtraBold,
        )
        val budget = child.budgetRand
        if (budget != null) {
            Text(
                text = stringResource(R.string.parent_home_of_budget, budget),
                color = Color.White.copy(alpha = 0.85f),
                fontSize = 12.sp,
            )
        }
        Row(
            horizontalArrangement = Arrangement.spacedBy(10.dp),
            modifier = Modifier.padding(top = 14.dp),
        ) {
            Button(
                onClick = onMyTasks,
                shape = PillShape,
                colors = ButtonDefaults.buttonColors(containerColor = Color.White, contentColor = Color(0xFF161B2E)),
                contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 24.dp, vertical = 12.dp),
            ) { Text(stringResource(R.string.parent_home_my_tasks), fontWeight = FontWeight.Bold) }
            OutlinedButton(
                onClick = onPayslip,
                shape = PillShape,
                colors = ButtonDefaults.outlinedButtonColors(contentColor = Color.White),
                contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 24.dp, vertical = 12.dp),
            ) { Text(stringResource(R.string.parent_home_payslip), fontWeight = FontWeight.Bold) }
        }
    }
}

@Composable
private fun AddChildDialog(
    state: AddChildState,
    onNameChanged: (String) -> Unit,
    onAgeBandSelected: (AgeBand) -> Unit,
    onChildEmailChanged: (String) -> Unit,
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
                Text(
                    text = stringResource(R.string.parent_add_child_link_hint),
                    style = MaterialTheme.typography.labelMedium,
                    modifier = Modifier.padding(top = 16.dp, bottom = 4.dp),
                )
                OutlinedTextField(
                    value = state.childEmail,
                    onValueChange = onChildEmailChanged,
                    label = { Text(stringResource(R.string.parent_add_child_email_label)) },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
                if (state.error == AppError.Conflict) {
                    Text(
                        text = stringResource(R.string.parent_add_child_limit),
                        color = MaterialTheme.colorScheme.error,
                        style = MaterialTheme.typography.bodySmall,
                        modifier = Modifier.padding(top = 8.dp),
                    )
                }
                if (state.linkError != null) {
                    Text(
                        text = if (state.linkError == AppError.Conflict) {
                            stringResource(R.string.parent_add_child_link_conflict)
                        } else {
                            stringResource(R.string.parent_add_child_link_failed)
                        },
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
