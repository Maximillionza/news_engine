package com.minimoney.app.data.auth

import com.minimoney.app.domain.auth.AuthError
import com.minimoney.app.domain.auth.AuthResult
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.mockk
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.runTest
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import retrofit2.HttpException
import retrofit2.Response
import java.io.IOException

class AuthRepositoryImplTest {

    private val api: AuthApi = mockk()
    private val sessionStore: SessionStore = mockk(relaxed = true)

    private fun httpException(code: Int) = HttpException(
        Response.error<Any>(code, "{}".toResponseBody("application/json".toMediaType())),
    )

    @Test
    fun `verify success persists session`() = runTest {
        val repo = AuthRepositoryImpl(api, sessionStore, StandardTestDispatcher(testScheduler))
        coEvery { api.verifyOtp(any()) } returns OtpVerifyResponse(
            parentAccountId = "acc-1", accessToken = "tok", consentComplete = false,
        )

        val result = repo.verifyOtp("ch-1", "123456")

        assertTrue(result is AuthResult.Success)
        coVerify(exactly = 1) { sessionStore.save(any()) }
        // consentComplete=false must survive the mapping — it routes the UI to the consent flow.
        assertEquals(false, (result as AuthResult.Success).value.consentComplete)
    }

    @Test
    fun `verify failure does not persist session`() = runTest {
        val repo = AuthRepositoryImpl(api, sessionStore, StandardTestDispatcher(testScheduler))
        coEvery { api.verifyOtp(any()) } throws httpException(401)

        val result = repo.verifyOtp("ch-1", "000000")

        assertEquals(AuthResult.Failure(AuthError.OtpMismatch), result)
        coVerify(exactly = 0) { sessionStore.save(any()) }
    }

    @Test
    fun `expired code maps to OtpExpired`() = runTest {
        val repo = AuthRepositoryImpl(api, sessionStore, StandardTestDispatcher(testScheduler))
        coEvery { api.verifyOtp(any()) } throws httpException(410)

        assertEquals(
            AuthResult.Failure(AuthError.OtpExpired),
            repo.verifyOtp("ch-1", "123456"),
        )
    }

    @Test
    fun `rate limit on request maps to TooManyAttempts`() = runTest {
        val repo = AuthRepositoryImpl(api, sessionStore, StandardTestDispatcher(testScheduler))
        coEvery { api.requestOtp(any()) } throws httpException(429)

        assertEquals(
            AuthResult.Failure(AuthError.TooManyAttempts),
            repo.requestOtp("+27821234567"),
        )
    }

    @Test
    fun `io failure maps to Network`() = runTest {
        val repo = AuthRepositoryImpl(api, sessionStore, StandardTestDispatcher(testScheduler))
        coEvery { api.requestOtp(any()) } throws IOException("offline")

        assertEquals(
            AuthResult.Failure(AuthError.Network),
            repo.requestOtp("+27821234567"),
        )
    }
}
