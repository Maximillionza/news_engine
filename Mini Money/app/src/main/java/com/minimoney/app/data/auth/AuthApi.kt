package com.minimoney.app.data.auth

import retrofit2.http.Body
import retrofit2.http.POST

/**
 * Parent auth: Google Sign-In only, verified server-side (supabase/functions/
 * auth-google). No password, no phone/OTP path — decision made 2026-07-15 to
 * replace phone+OTP entirely rather than run two parent-auth paths.
 */
interface AuthApi {

    @POST("auth-google")
    suspend fun signInWithGoogle(@Body body: GoogleSignInBody): GoogleSignInResponse
}
