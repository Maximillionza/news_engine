package com.minimoney.app

import android.app.Application
import androidx.hilt.work.HiltWorkerFactory
import androidx.work.Configuration
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import com.minimoney.app.work.DisputeSlaWorker
import com.minimoney.app.work.PayslipReminderWorker
import dagger.hilt.android.HiltAndroidApp
import java.util.concurrent.TimeUnit
import javax.inject.Inject

@HiltAndroidApp
class MiniMoneyApp : Application(), Configuration.Provider {

    @Inject
    lateinit var workerFactory: HiltWorkerFactory

    override val workManagerConfiguration: Configuration
        get() = Configuration.Builder().setWorkerFactory(workerFactory).build()

    override fun onCreate() {
        super.onCreate()
        scheduleDailyChecks()
    }

    /** Daily grace-period and dispute-SLA checks — WorkManager, no server cron. */
    private fun scheduleDailyChecks() {
        val workManager = WorkManager.getInstance(this)
        workManager.enqueueUniquePeriodicWork(
            PayslipReminderWorker.WORK_NAME,
            ExistingPeriodicWorkPolicy.KEEP,
            PeriodicWorkRequestBuilder<PayslipReminderWorker>(1, TimeUnit.DAYS).build(),
        )
        workManager.enqueueUniquePeriodicWork(
            DisputeSlaWorker.WORK_NAME,
            ExistingPeriodicWorkPolicy.KEEP,
            PeriodicWorkRequestBuilder<DisputeSlaWorker>(1, TimeUnit.DAYS).build(),
        )
    }
}
