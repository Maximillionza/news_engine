package com.minimoney.app.presentation

import androidx.compose.runtime.Composable
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.minimoney.app.BuildConfig
import com.minimoney.app.presentation.child.ChildDetailRoute
import com.minimoney.app.presentation.exambonus.ExamBonusRoute
import com.minimoney.app.presentation.home.HomeRoute
import com.minimoney.app.presentation.linking.AccountLinkingRoute
import com.minimoney.app.presentation.more.MoreRoute
import com.minimoney.app.presentation.profile.ProfileRoute
import com.minimoney.app.presentation.mpoints.MpointsRoute
import com.minimoney.app.presentation.payslips.PayslipsRoute
import com.minimoney.app.presentation.tasks.ChildTasksRoute
import com.minimoney.app.presentation.tasks.TasksRoute

/** Signed-in, consent-complete area. The session-driven root gates entry here. */
@Composable
fun ParentNavGraph() {
    val navController = rememberNavController()
    val childIdArg = navArgument("childId") { type = NavType.LongType }

    NavHost(navController = navController, startDestination = "home") {
        composable("home") {
            HomeRoute(
                onOpenChild = { navController.navigate("child/$it") },
                onOpenTasks = { navController.navigate("child/$it/tasks") },
                onOpenPayslips = { navController.navigate("child/$it/payslips") },
                onOpenAccountLinking = { navController.navigate("linking") },
                onOpenMore = { navController.navigate("more") },
                onOpenProfile = { navController.navigate("profile") },
            )
        }
        composable("profile") { ProfileRoute() }
        composable("more") {
            MoreRoute(
                // Per-child tools (disputes, penalties, exam bonus, Mpoints) all
                // start from picking a child, so their tiles land on Home.
                onOpenHome = { navController.popBackStack("home", inclusive = false) },
                onOpenProfile = { navController.navigate("profile") },
                onOpenExamBonus = { navController.popBackStack("home", inclusive = false) },
                onOpenMpoints = { navController.popBackStack("home", inclusive = false) },
                onOpenLinking = { navController.navigate("linking") },
            )
        }
        // Flag-gated: entry point only rendered while ACCOUNT_LINKING_ENABLED is on.
        composable("linking") { AccountLinkingRoute() }
        composable("child/{childId}", arguments = listOf(childIdArg)) {
            ChildDetailRoute(
                onOpenTasks = { navController.navigate("child/$it/tasks") },
                onOpenPayslips = { navController.navigate("child/$it/payslips") },
                onOpenChildView = { navController.navigate("child/$it/childview") },
            )
        }
        composable("child/{childId}/tasks", arguments = listOf(childIdArg)) { TasksRoute() }
        composable("child/{childId}/payslips", arguments = listOf(childIdArg)) { PayslipsRoute() }
        composable("child/{childId}/childview", arguments = listOf(childIdArg)) { ChildTasksRoute() }
        // Flag-gated: only reachable while MPOINTS_ENABLED is on (OFF at launch).
        composable("child/{childId}/mpoints", arguments = listOf(childIdArg)) { MpointsRoute() }
        // Debug builds only: exam-bonus is build/QA-with-test-data until the
        // child-development specialist's review has documented sign-off.
        if (BuildConfig.DEBUG) {
            composable("child/{childId}/exambonus", arguments = listOf(childIdArg)) { ExamBonusRoute() }
        }
    }
}
