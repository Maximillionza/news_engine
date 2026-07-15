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
import okhttp3.Interceptor
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Protocol
import okhttp3.Response
import okhttp3.ResponseBody.Companion.toResponseBody
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

    @Provides
    @Singleton
    fun provideOkHttp(): OkHttpClient {
        val builder = OkHttpClient.Builder()
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(15, TimeUnit.SECONDS)

        // Debug mode: mock OTP endpoints for device testing without a backend.
        if (BuildConfig.DEBUG) {
            builder.addInterceptor(Interceptor { chain ->
                val request = chain.request()
                val path = request.url.encodedPath

                when {
                    path.contains("/auth/otp/request") -> Response.Builder()
                        .request(request)
                        .protocol(Protocol.HTTP_1_1)
                        .code(200)
                        .message("OK")
                        .body(
                            """{"challenge_id":"mock-challenge-1","expires_in_seconds":300,"resend_allowed_in_seconds":30}"""
                                .toResponseBody("application/json".toMediaType()),
                        )
                        .build()
                    path.contains("/auth/otp/verify") -> Response.Builder()
                        .request(request)
                        .protocol(Protocol.HTTP_1_1)
                        .code(200)
                        .message("OK")
                        .body(
                            """{"parent_account_id":"acc-test","access_token":"mock-token","consent_complete":false}"""
                                .toResponseBody("application/json".toMediaType()),
                        )
                        .build()
                    path.contains("/consent/current") -> Response.Builder()
                        .request(request)
                        .protocol(Protocol.HTTP_1_1)
                        .code(200)
                        .message("OK")
                        .body(
                            """{"version":"v1","sections":[{"title":"Why we ask","body":"MiniMoney needs your consent to record your child's task activity and Mbuck earnings locally on this device."},{"title":"What we store","body":"Phone number, child names and ages, task history, and Mbuck ledger entries. Nothing is sold or shared with third parties."}]}"""
                                .toResponseBody("application/json".toMediaType()),
                        )
                        .build()
                    path.contains("/consent/accept") -> Response.Builder()
                        .request(request)
                        .protocol(Protocol.HTTP_1_1)
                        .code(200)
                        .message("OK")
                        .body(
                            """{"document_version":"v1","accepted_at_epoch_millis":${System.currentTimeMillis()}}"""
                                .toResponseBody("application/json".toMediaType()),
                        )
                        .build()
                    else -> chain.proceed(request)
                }
            })
        }

        return builder.build()
    }

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
    fun provideIoDispatcher(): CoroutineDispatcher = Dispatchers.IO
}
