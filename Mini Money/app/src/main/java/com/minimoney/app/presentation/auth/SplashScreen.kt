package com.minimoney.app.presentation.auth

import androidx.compose.animation.core.EaseInOutSine
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.minimoney.app.R
import com.minimoney.app.ui.theme.MiniMoneyTheme
import com.minimoney.app.ui.theme.PillShape

/**
 * Splash (handoff §Screens 1): brand moment + entry point. The mock's
 * separate Register/Login paths collapsed into one Google Sign-In flow
 * (auth decision 2026-07-15), so both buttons lead to the same screen —
 * kept as two affordances because new-vs-returning framing still helps.
 */
@Composable
fun SplashScreen(onGetStarted: () -> Unit) {
    val colors = MiniMoneyTheme.colors
    val drift = rememberInfiniteTransition(label = "splash-drift")
    val dotOffset by drift.animateFloat(
        initialValue = -6f,
        targetValue = 6f,
        animationSpec = infiniteRepeatable(tween(4200, easing = EaseInOutSine), RepeatMode.Reverse),
        label = "dot-offset",
    )
    val logoPop by drift.animateFloat(
        initialValue = 0.96f,
        targetValue = 1.0f,
        animationSpec = infiniteRepeatable(tween(2600, easing = EaseInOutSine), RepeatMode.Reverse),
        label = "logo-breathe",
    )

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(colors.background),
    ) {
        // Two soft radial glows behind the content (top-left, bottom-right).
        Box(
            Modifier
                .size(280.dp)
                .offset(x = (-80).dp, y = (-60).dp)
                .background(
                    Brush.radialGradient(
                        listOf(colors.accentSolid.copy(alpha = 0.25f), Color.Transparent),
                    ),
                ),
        )
        Box(
            Modifier
                .size(280.dp)
                .align(Alignment.BottomEnd)
                .offset(x = 80.dp, y = 60.dp)
                .background(
                    Brush.radialGradient(
                        listOf(Color(0xFFA26CF0).copy(alpha = 0.22f), Color.Transparent),
                    ),
                ),
        )
        // Decorative floating dots.
        listOf(
            Triple(0.18f, 0.22f, 8.dp),
            Triple(0.82f, 0.30f, 6.dp),
            Triple(0.70f, 0.72f, 7.dp),
        ).forEachIndexed { index, (xFrac, yFrac, dotSize) ->
            Box(
                Modifier
                    .align(Alignment.TopStart)
                    .fillMaxSize(),
            ) {
                Box(
                    Modifier
                        .align(BiasAlignmentFor(xFrac, yFrac))
                        .offset(y = (if (index % 2 == 0) dotOffset else -dotOffset).dp)
                        .size(dotSize)
                        .background(colors.text.copy(alpha = 0.18f), CircleShape),
                )
            }
        }

        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 28.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Column(
                modifier = Modifier.weight(0.7f),
                verticalArrangement = androidx.compose.foundation.layout.Arrangement.Center,
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Box(
                    modifier = Modifier
                        .size(96.dp)
                        .scale(logoPop)
                        .background(colors.accentGradient, CircleShape),
                    contentAlignment = Alignment.Center,
                ) {
                    Text("M", color = Color.White, fontSize = 40.sp, fontWeight = FontWeight.ExtraBold)
                }
                Text(
                    text = stringResource(R.string.parent_splash_wordmark),
                    color = colors.text,
                    fontSize = 24.sp,
                    fontWeight = FontWeight.ExtraBold,
                    modifier = Modifier.padding(top = 20.dp),
                )
                Text(
                    text = stringResource(R.string.parent_splash_tagline),
                    color = colors.textMuted,
                    fontSize = 13.sp,
                    modifier = Modifier.padding(top = 6.dp),
                )
            }
            Column(
                modifier = Modifier
                    .weight(0.3f)
                    .fillMaxWidth(),
                verticalArrangement = androidx.compose.foundation.layout.Arrangement.Center,
            ) {
                Button(
                    onClick = onGetStarted,
                    shape = PillShape,
                    colors = ButtonDefaults.buttonColors(containerColor = colors.accentSolid),
                    contentPadding = androidx.compose.foundation.layout.PaddingValues(vertical = 16.dp),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text(
                        stringResource(R.string.parent_splash_get_started),
                        fontWeight = FontWeight.Bold,
                        color = Color.White,
                    )
                }
                TextButton(
                    onClick = onGetStarted,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 4.dp),
                ) {
                    Text(stringResource(R.string.parent_splash_log_in), color = colors.textMuted)
                }
            }
        }
    }
}

private fun BiasAlignmentFor(xFrac: Float, yFrac: Float) =
    androidx.compose.ui.BiasAlignment(horizontalBias = xFrac * 2 - 1, verticalBias = yFrac * 2 - 1)
