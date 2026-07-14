package com.minimoney.app.di

import android.content.Context
import androidx.room.Room
import com.minimoney.app.data.consent.ConsentApi
import com.minimoney.app.data.consent.ConsentRepositoryImpl
import com.minimoney.app.data.db.ConsentDao
import com.minimoney.app.data.db.MiniMoneyDatabase
import com.minimoney.app.domain.consent.ConsentRepository
import dagger.Binds
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import retrofit2.Retrofit
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
abstract class ConsentModule {

    @Binds
    abstract fun bindConsentRepository(impl: ConsentRepositoryImpl): ConsentRepository

    companion object {
        @Provides
        @Singleton
        fun provideDatabase(@ApplicationContext context: Context): MiniMoneyDatabase =
            Room.databaseBuilder(context, MiniMoneyDatabase::class.java, "minimoney.db")
                .addMigrations(
                    com.minimoney.app.data.db.MIGRATION_1_2,
                    com.minimoney.app.data.db.MIGRATION_2_3,
                )
                .build()

        @Provides
        fun provideConsentDao(db: MiniMoneyDatabase): ConsentDao = db.consentDao()

        @Provides
        @Singleton
        fun provideConsentApi(retrofit: Retrofit): ConsentApi =
            retrofit.create(ConsentApi::class.java)
    }
}
