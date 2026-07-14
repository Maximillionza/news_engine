package com.minimoney.app.data.auth

import com.minimoney.app.domain.auth.AuthError
import com.minimoney.app.domain.auth.AuthRepository
import com.minimoney.app.domain.auth.AuthResult
import com.minimoney.app.domain.auth.OtpChallenge
import com.minimoney.app.domain.auth.ParentSession
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.withContext
import retrofit2.HttpException
import java.io.IOException
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AuthRepositoryImpl @Inject constructor(
    private val api: AuthApi,
    private val sessionStore: SessionStore,
    private val ioDispatcher: CoroutineDispatcher,
) : AuthRepository {

    override val session: Flow<ParentSession?> = sessionStore.session

    override suspend fun requestOtp(phoneE164: String): AuthResult<OtpChallenge> =
        safeCall(
            call = { api.requestOtp(OtpRequestBody(phoneE164)) },
            mapHttpError = ::mapRequestError,
        ) { resp ->
            OtpChallenge(
                challengeId = resp.challengeId,
                phoneE164 = phoneE164,
                expiresInSeconds = resp.expiresInSeconds,
                resendAllowedInSeconds = resp.resendAllowedInSeconds,
            )
        }

    override suspend fun verifyOtp(challengeId: String, code: String): AuthResult<ParentSession> {
        val result = safeCall(
            call = { api.verifyOtp(OtpVerifyBody(challengeId, code)) },
            mapHttpError = ::mapVerifyError,
        ) { resp ->
            ParentSession(
                parentAccountId = resp.parentAccountId,
                accessToken = resp.accessToken,
                consentComplete = resp.consentComplete,
            )
        }
        // Persist only after a fully successful verify — never store a token
        // from a failed or partial response.
        if (result is AuthResult.Success) {
            sessionStore.save(result.value)
        }
        return result
    }

    override suspend fun signOut() {
        sessionStore.clear()
    }

    /** Runs a network call on IO, converting exceptions into typed AuthErrors. */
    private suspend fun <Dto, T> safeCall(
        call: suspend () -> Dto,
        mapHttpError: (Int) -> AuthError,
        transform: (Dto) -> T,
    ): AuthResult<T> = withContext(ioDispatcher) {
        try {
            AuthResult.Success(transform(call()))
        } catch (e: HttpException) {
            AuthResult.Failure(mapHttpError(e.code()))
        } catch (e: IOException) {
            AuthResult.Failure(AuthError.Network)
        } catch (e: Exception) {
            AuthResult.Failure(AuthError.Unknown(e))
        }
    }

    private fun mapRequestError(httpCode: Int): AuthError = when (httpCode) {
        400 -> AuthError.InvalidPhoneNumber
        429 -> AuthError.TooManyAttempts
        in 500..599 -> AuthError.Server(httpCode)
        else -> AuthError.Unknown()
    }

    private fun mapVerifyError(httpCode: Int): AuthError = when (httpCode) {
        400, 401, 422 -> AuthError.OtpMismatch
        410 -> AuthError.OtpExpired
        429 -> AuthError.TooManyAttempts
        in 500..599 -> AuthError.Server(httpCode)
        else -> AuthError.Unknown()
    }
}
