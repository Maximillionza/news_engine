package com.minimoney.app.di

import com.minimoney.app.BuildConfig
import com.minimoney.app.data.auth.AuthApi
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import java.util.concurrent.TimeUnit
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    @Provides
    @Singleton
    fun provideJson(): Json = Json {
        // Tolerate additive server-side API changes without a client release.
        ignoreUnknownKeys = true
    }

    // The pre-backend debug mock interceptor was removed 2026-07-15 when the
    // Supabase project went live — debug builds now exercise the real
    // endpoints end-to-end (git history has the mock if it's ever needed).
    @Provides
    @Singleton
    fun provideOkHttp(authInterceptor: AuthInterceptor): OkHttpClient =
        OkHttpClient.Builder()
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(15, TimeUnit.SECONDS)
            .addInterceptor(authInterceptor)
            .build()

    @Provides
    @Singleton
    fun provideRetrofit(json: Json, client: OkHttpClient): Retrofit = Retrofit.Builder()
        .baseUrl(BuildConfig.API_BASE_URL)
        .client(client)
        .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
        .build()

    @Provides
    @Singleton
    fun provideAuthApi(retrofit: Retrofit): AuthApi = retrofit.create(AuthApi::class.java)

    @Provides
    @Singleton
    fun provideLinkChildApi(retrofit: Retrofit): com.minimoney.app.data.child.LinkChildApi =
        retrofit.create(com.minimoney.app.data.child.LinkChildApi::class.java)

    @Provides
    fun provideIoDispatcher(): CoroutineDispatcher = Dispatchers.IO
}
