package com.minimoney.app.di

import com.minimoney.app.data.auth.SessionStore
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import okhttp3.Interceptor
import okhttp3.Response
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Attaches the current parent session's access token as a Bearer header on
 * every outgoing request. Endpoints that don't require auth (auth-google,
 * access-check, consent-current) simply ignore the header server-side —
 * see requireParentAuth in the Edge Functions, which only the
 * parent-scoped endpoints call.
 */
@Singleton
class AuthInterceptor @Inject constructor(
    private val sessionStore: SessionStore,
) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        // OkHttp interceptors are synchronous; DataStore reads are cheap and
        // already in-memory-cached after the first read, so blocking here is
        // negligible compared to the network call this precedes.
        val token = runBlocking { sessionStore.session.first() }?.accessToken
        val request = if (token != null) {
            chain.request().newBuilder().addHeader("Authorization", "Bearer $token").build()
        } else {
            chain.request()
        }
        return chain.proceed(request)
    }
}
