package com.minimoney.app.data.child

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import retrofit2.http.Body
import retrofit2.http.POST

interface LinkChildApi {
    /** Parent-authenticated (Bearer, attached by AuthInterceptor). 409 if the email is already linked/pending. */
    @POST("link-child")
    suspend fun linkChild(@Body body: LinkChildBody): LinkChildResponse
}

@Serializable
data class LinkChildBody(
    @SerialName("email") val email: String,
    @SerialName("display_name") val displayName: String?,
    @SerialName("age_band") val ageBand: String,
)

@Serializable
data class LinkChildResponse(
    @SerialName("child_link_id") val childLinkId: String,
    @SerialName("email") val email: String,
    @SerialName("display_name") val displayName: String?,
    @SerialName("age_band") val ageBand: String,
    @SerialName("status") val status: String,
)
