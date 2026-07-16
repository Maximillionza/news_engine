package com.minimoney.app.presentation.auth

import android.content.Context
import androidx.credentials.CredentialManager
import androidx.credentials.GetCredentialRequest
import androidx.credentials.exceptions.GetCredentialCancellationException
import androidx.credentials.exceptions.GetCredentialException
import androidx.credentials.exceptions.NoCredentialException
import com.google.android.libraries.identity.googleid.GetSignInWithGoogleOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import com.google.android.libraries.identity.googleid.GoogleIdTokenParsingException
import com.minimoney.app.domain.auth.AuthError

sealed interface GoogleSignInOutcome {
    data class Success(val idToken: String) : GoogleSignInOutcome
    data class Failure(val error: AuthError) : GoogleSignInOutcome
}

/**
 * Credential Manager needs an Activity Context — that's why this lives at
 * the UI layer rather than in AuthRepository, which stays Android-free.
 * Only the resulting ID token crosses into the ViewModel/repository; the
 * server re-verifies it independently, so nothing here is trusted blindly.
 */
suspend fun launchGoogleSignIn(context: Context, webClientId: String): GoogleSignInOutcome {
    val option = GetSignInWithGoogleOption.Builder(webClientId).build()
    val request = GetCredentialRequest.Builder().addCredentialOption(option).build()

    return try {
        val response = CredentialManager.create(context).getCredential(context, request)
        val googleIdTokenCredential = GoogleIdTokenCredential.createFrom(response.credential.data)
        GoogleSignInOutcome.Success(googleIdTokenCredential.idToken)
    } catch (e: GetCredentialCancellationException) {
        GoogleSignInOutcome.Failure(AuthError.SignInCancelled)
    } catch (e: NoCredentialException) {
        GoogleSignInOutcome.Failure(AuthError.NoGoogleAccount)
    } catch (e: GoogleIdTokenParsingException) {
        GoogleSignInOutcome.Failure(AuthError.Unknown(e))
    } catch (e: GetCredentialException) {
        GoogleSignInOutcome.Failure(AuthError.Unknown(e))
    }
}
