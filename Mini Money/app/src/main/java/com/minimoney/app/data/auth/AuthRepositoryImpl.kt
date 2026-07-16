package com.minimoney.app.data.auth

import com.minimoney.app.domain.auth.AuthError
import com.minimoney.app.domain.auth.AuthRepository
import com.minimoney.app.domain.auth.AuthResult
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

    override suspend fun signInWithGoogle(googleIdToken: String): AuthResult<ParentSession> {
        val result = withContext(ioDispatcher) {
            try {
                val resp = api.signInWithGoogle(GoogleSignInBody(googleIdToken))
                AuthResult.Success(
                    ParentSession(
                        parentAccountId = resp.parentAccountId,
                        accessToken = resp.accessToken,
                        consentComplete = resp.consentComplete,
                    ),
                )
            } catch (e: HttpException) {
                AuthResult.Failure(
                    when (e.code()) {
                        in 500..599 -> AuthError.Server(e.code())
                        else -> AuthError.Unknown(e) // 400/401 here mean the token itself was rejected server-side
                    },
                )
            } catch (e: IOException) {
                AuthResult.Failure(AuthError.Network)
            } catch (e: Exception) {
                AuthResult.Failure(AuthError.Unknown(e))
            }
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
}
