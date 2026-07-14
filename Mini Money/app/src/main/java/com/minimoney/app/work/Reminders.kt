package com.minimoney.app.work

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.hilt.work.HiltWorker
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.minimoney.app.R
import com.minimoney.app.data.db.DisputeDao
import com.minimoney.app.data.db.PayslipDao
import com.minimoney.app.domain.core.Clock
import com.minimoney.app.domain.dispute.DisputeSla
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import kotlinx.coroutines.flow.first

/** All reminder notifications are PARENT-FACING only — none target a child surface. */
object ReminderChannel {
    const val ID = "parent_reminders"

    fun ensure(context: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val manager = context.getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(
                NotificationChannel(ID, "Reminders", NotificationManager.IMPORTANCE_DEFAULT),
            )
        }
    }

    fun notify(context: Context, notificationId: Int, title: String, body: String) {
        ensure(context)
        // No POST_NOTIFICATIONS permission = reminder silently skipped; the
        // in-app payslip state remains the source of truth.
        if (!NotificationManagerCompat.from(context).areNotificationsEnabled()) return
        val notification = NotificationCompat.Builder(context, ID)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle(title)
            .setContentText(body)
            .setAutoCancel(true)
            .build()
        try {
            NotificationManagerCompat.from(context).notify(notificationId, notification)
        } catch (_: SecurityException) {
            // Permission revoked between the check and the call — skip, never crash.
        }
    }
}

/**
 * Grace-period / pre-escalation reminder (PRD Core Feature 10): before any
 * late-penalty step is applied, the parent gets a reminder that a payslip is
 * awaiting payment. Runs daily via WorkManager — no server-side cron, per the
 * minimal-backend approach (BuildSpec §Third-Party Dependencies).
 */
@HiltWorker
class PayslipReminderWorker @AssistedInject constructor(
    @Assisted appContext: Context,
    @Assisted params: WorkerParameters,
    private val payslipDao: PayslipDao,
    private val clock: Clock,
) : CoroutineWorker(appContext, params) {

    override suspend fun doWork(): Result {
        val cutoff = clock.nowMillis() - GRACE_PERIOD_MILLIS
        val overdue = payslipDao.generatedOlderThan(cutoff)
        if (overdue.isNotEmpty()) {
            ReminderChannel.notify(
                applicationContext,
                notificationId = 1001,
                title = applicationContext.getString(R.string.parent_reminder_payslip_title),
                body = applicationContext.getString(
                    R.string.parent_reminder_payslip_body, overdue.size,
                ),
            )
        }
        return Result.success()
    }

    companion object {
        // Grace period before the reminder (and any penalty escalation step)
        // fires. Whole days; a direct setting, not a derived calculation.
        const val GRACE_PERIOD_DAYS = 7
        const val GRACE_PERIOD_MILLIS = GRACE_PERIOD_DAYS * 24L * 60 * 60 * 1000
        const val WORK_NAME = "payslip_reminder"
    }
}

/**
 * Dispute-SLA watchdog: surfaces disputes past the 48h window and raises the
 * capacity-threshold alarm (BuildSpec §Operations) when more than 5 are
 * concurrently open past it — the trigger for the logged founder-capacity review.
 */
@HiltWorker
class DisputeSlaWorker @AssistedInject constructor(
    @Assisted appContext: Context,
    @Assisted params: WorkerParameters,
    private val disputeDao: DisputeDao,
    private val clock: Clock,
) : CoroutineWorker(appContext, params) {

    override suspend fun doWork(): Result {
        val cutoff = clock.nowMillis() - DisputeSla.DECISION_WINDOW_MILLIS
        val pastWindow = disputeDao.openOlderThanCount(cutoff).first()
        if (pastWindow > 0) {
            ReminderChannel.notify(
                applicationContext,
                notificationId = 1002,
                title = applicationContext.getString(R.string.parent_reminder_dispute_title),
                body = applicationContext.getString(
                    R.string.parent_reminder_dispute_body, pastWindow,
                ),
            )
        }
        if (DisputeSla.capacityThresholdCrossed(pastWindow, null)) {
            // Interim mechanism deemed FAILED — logged, explicit trigger.
            android.util.Log.w(
                "DisputeSla",
                "Capacity threshold crossed: $pastWindow disputes open past 48h. " +
                    "Founder-capacity review required (BuildSpec §Operations).",
            )
        }
        return Result.success()
    }

    companion object {
        const val WORK_NAME = "dispute_sla_check"
    }
}
