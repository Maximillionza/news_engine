package com.minimoney.app.di

import com.minimoney.app.BuildConfig
import com.minimoney.app.data.child.ChildRepositoryImpl
import com.minimoney.app.data.db.ChildDao
import com.minimoney.app.data.db.DisputeDao
import com.minimoney.app.data.db.LedgerDao
import com.minimoney.app.data.db.MiniMoneyDatabase
import com.minimoney.app.data.db.PayslipDao
import com.minimoney.app.data.db.TaskDao
import com.minimoney.app.data.dispute.DisputeRepositoryImpl
import com.minimoney.app.data.flags.FeatureFlagsImpl
import com.minimoney.app.data.payslip.PayslipRepositoryImpl
import com.minimoney.app.data.tasks.TaskRepositoryImpl
import com.minimoney.app.domain.child.ChildRepository
import com.minimoney.app.domain.core.Clock
import com.minimoney.app.domain.dispute.DisputeRepository
import com.minimoney.app.domain.flags.FeatureFlags
import com.minimoney.app.domain.payslip.PayslipRepository
import com.minimoney.app.domain.tasks.TaskRepository
import dagger.Binds
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Named

@Module
@InstallIn(SingletonComponent::class)
abstract class CoreModule {

    @Binds
    abstract fun bindChildRepository(impl: ChildRepositoryImpl): ChildRepository

    @Binds
    abstract fun bindTaskRepository(impl: TaskRepositoryImpl): TaskRepository

    @Binds
    abstract fun bindPayslipRepository(impl: PayslipRepositoryImpl): PayslipRepository

    @Binds
    abstract fun bindDisputeRepository(impl: DisputeRepositoryImpl): DisputeRepository

    @Binds
    abstract fun bindFeatureFlags(impl: FeatureFlagsImpl): FeatureFlags

    companion object {
        @Provides
        fun provideClock(): Clock = Clock { System.currentTimeMillis() }

        @Provides
        @Named("is_pilot")
        fun provideIsPilot(): Boolean = BuildConfig.IS_PILOT

        @Provides
        fun provideChildDao(db: MiniMoneyDatabase): ChildDao = db.childDao()

        @Provides
        fun provideTaskDao(db: MiniMoneyDatabase): TaskDao = db.taskDao()

        @Provides
        fun provideLedgerDao(db: MiniMoneyDatabase): LedgerDao = db.ledgerDao()

        @Provides
        fun providePayslipDao(db: MiniMoneyDatabase): PayslipDao = db.payslipDao()

        @Provides
        fun provideDisputeDao(db: MiniMoneyDatabase): DisputeDao = db.disputeDao()

        @Provides
        fun provideExamBonusDao(db: MiniMoneyDatabase): com.minimoney.app.data.db.ExamBonusDao =
            db.examBonusDao()
    }
}
