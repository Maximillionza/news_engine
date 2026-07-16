package com.minimoney.app.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

/**
 * Design tokens from design_handoff_mini_money_app/README.md §Design Tokens.
 * Values are final design intent, not placeholders — change only against an
 * updated handoff. One token object per theme; the Profile dark-mode toggle
 * swaps them (design: "one token object swaps", not separate screens).
 */
@Immutable
data class MiniMoneyColors(
    val background: Color,
    val surface: Color,
    val surface2: Color,
    val text: Color,
    val textMuted: Color,
    val divider: Color,
    val accentSolid: Color,
    val accentText: Color,
    val accentGradient: Brush,
    val successSoft: Color,
    val successText: Color,
)

val DarkTokens = MiniMoneyColors(
    background = Color(0xFF0C1220),
    surface = Color(0xFF161D30),
    surface2 = Color(0xFF1E2740),
    text = Color(0xFFF4F6FB),
    textMuted = Color(0xFFF4F6FB).copy(alpha = 0.58f),
    divider = Color(0xFFF4F6FB).copy(alpha = 0.14f),
    accentSolid = Color(0xFF6C8DFF),
    accentText = Color(0xFF93A9FF),
    accentGradient = Brush.linearGradient(listOf(Color(0xFF6C8DFF), Color(0xFFA26CF0))),
    successSoft = Color(0xFF33D17A).copy(alpha = 0.16f),
    successText = Color(0xFF33D17A),
)

val LightTokens = MiniMoneyColors(
    background = Color(0xFFF4F5FA),
    surface = Color(0xFFFFFFFF),
    surface2 = Color(0xFFECEEF7),
    text = Color(0xFF161B2E),
    textMuted = Color(0xFF161B2E).copy(alpha = 0.58f),
    divider = Color(0xFF161B2E).copy(alpha = 0.12f),
    accentSolid = Color(0xFF4C6BEF),
    accentText = Color(0xFF3D55C9),
    accentGradient = Brush.linearGradient(listOf(Color(0xFF4C6BEF), Color(0xFF8A4CEF))),
    successSoft = Color(0xFF18A35E).copy(alpha = 0.14f),
    successText = Color(0xFF189A5A),
)

/**
 * Per-child hero-card gradients (handoff §Design Tokens) — decorative,
 * assigned by cycling on the child's stable id so each card stays visually
 * distinct and consistent across sessions.
 */
private val ChildGradientPalettes: List<List<Color>> = listOf(
    listOf(Color(0xFF6A5CF0), Color(0xFFA24BD8), Color(0xFFE94F9A)),
    listOf(Color(0xFF2F8BF0), Color(0xFF4FD6C4)),
    listOf(Color(0xFFF0A24B), Color(0xFFE9574F), Color(0xFFC94BD8)),
    listOf(Color(0xFF33D17A), Color(0xFF2F8BF0)),
)

fun childGradient(childId: Long): Brush =
    Brush.linearGradient(ChildGradientPalettes[(childId % ChildGradientPalettes.size).toInt()])

val LocalMiniMoneyColors = staticCompositionLocalOf { DarkTokens }

/** Shape system (handoff §Shape & spacing): pill buttons, tiered card radii. */
val PillShape = RoundedCornerShape(100.dp)
val HeroCardShape = RoundedCornerShape(24.dp)
val CardShape = RoundedCornerShape(18.dp)
val RowShape = RoundedCornerShape(16.dp)
val TileShape = RoundedCornerShape(12.dp)

object MiniMoneyTheme {
    val colors: MiniMoneyColors
        @Composable get() = LocalMiniMoneyColors.current
}

@Composable
fun MiniMoneyTheme(
    // Dark-first design; the system setting is only the starting default —
    // the in-app Profile toggle overrides it (wired via AppViewModel).
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    val tokens = if (darkTheme) DarkTokens else LightTokens

    // Material color scheme mapped from the tokens so stock M3 components
    // (dialogs, text fields, chips) blend in even before they're restyled.
    val colorScheme = if (darkTheme) {
        darkColorScheme(
            primary = tokens.accentSolid,
            onPrimary = Color.White,
            background = tokens.background,
            onBackground = tokens.text,
            surface = tokens.surface,
            onSurface = tokens.text,
            surfaceVariant = tokens.surface2,
            onSurfaceVariant = tokens.textMuted,
            outline = tokens.divider,
        )
    } else {
        lightColorScheme(
            primary = tokens.accentSolid,
            onPrimary = Color.White,
            background = tokens.background,
            onBackground = tokens.text,
            surface = tokens.surface,
            onSurface = tokens.text,
            surfaceVariant = tokens.surface2,
            onSurfaceVariant = tokens.textMuted,
            outline = tokens.divider,
        )
    }

    CompositionLocalProvider(LocalMiniMoneyColors provides tokens) {
        MaterialTheme(
            colorScheme = colorScheme,
            shapes = Shapes(
                extraSmall = TileShape,
                small = RowShape,
                medium = CardShape,
                large = HeroCardShape,
                extraLarge = PillShape,
            ),
            content = content,
        )
    }
}
