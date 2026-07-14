package com.minimoney.app.data.auth

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class OtpRequestBody(
    @SerialName("phone_e164") val phoneE164: String,
)

@Serializable
data class OtpRequestResponse(
    @SerialName("challenge_id") val challengeId: String,
    @SerialName("expires_in_seconds") val expiresInSeconds: Int,
    @SerialName("resend_allowed_in_seconds") val resendAllowedInSeconds: Int,
)

@Serializable
data class OtpVerifyBody(
    @SerialName("challenge_id") val challengeId: String,
    @SerialName("code") val code: String,
)

@Serializable
data class OtpVerifyResponse(
    @SerialName("parent_account_id") val parentAccountId: String,
    @SerialName("access_token") val accessToken: String,
    // Consent flow is a separate, versioned record (BuildSpec §Compliance);
    // the server reports whether the current consent-text version is accepted.
    @SerialName("consent_complete") val consentComplete: Boolean,
)
