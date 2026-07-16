package com.minimoney.app.data.auth

import com.minimoney.app.domain.auth.AuthError
import com.minimoney.app.domain.auth.AuthResult
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.mockk
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.TestScope
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

    private fun TestScope.repo() = AuthRepositoryImpl(api, sessionStore, StandardTestDispatcher(testScheduler))

    private fun httpException(code: Int) = HttpException(
        Response.error<Any>(code, "{}".toResponseBody("application/json".toMediaType())),
    )

    @Test
    fun `sign-in success persists session`() = runTest {
        coEvery { api.signInWithGoogle(any()) } returns GoogleSignInResponse(
            parentAccountId = "acc-1", accessToken = "tok", consentComplete = false,
        )

        val result = repo().signInWithGoogle("google-id-token")

        assertTrue(result is AuthResult.Success)
        coVerify(exactly = 1) { sessionStore.save(any()) }
        // consentComplete=false must survive the mapping — it routes the UI to the consent flow.
        assertEquals(false, (result as AuthResult.Success).value.consentComplete)
    }

    @Test
    fun `rejected token does not persist a session`() = runTest {
        coEvery { api.signInWithGoogle(any()) } throws httpException(401)

        val result = repo().signInWithGoogle("bad-token")

        assertTrue(result is AuthResult.Failure)
        coVerify(exactly = 0) { sessionStore.save(any()) }
    }

    @Test
    fun `server error maps to Server`() = runTest {
        coEvery { api.signInWithGoogle(any()) } throws httpException(500)

        assertEquals(AuthResult.Failure(AuthError.Server(500)), repo().signInWithGoogle("tok"))
    }

    @Test
    fun `io failure maps to Network`() = runTest {
        coEvery { api.signInWithGoogle(any()) } throws IOException("offline")

        assertEquals(AuthResult.Failure(AuthError.Network), repo().signInWithGoogle("tok"))
    }
}
