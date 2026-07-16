package com.minimoney.app.data.auth

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class GoogleSignInBody(
    @SerialName("id_token") val idToken: String,
)

@Serializable
data class GoogleSignInResponse(
    @SerialName("parent_account_id") val parentAccountId: String,
    @SerialName("access_token") val accessToken: String,
    // Consent flow is a separate, versioned record (BuildSpec §Compliance);
    // the server reports whether the current consent-text version is accepted.
    @SerialName("consent_complete") val consentComplete: Boolean,
)
