package com.minimoney.app.data.consent

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class ConsentSectionDto(
    @SerialName("title") val title: String,
    @SerialName("body") val body: String,
)

@Serializable
data class ConsentDocumentDto(
    @SerialName("version") val version: String,
    @SerialName("sections") val sections: List<ConsentSectionDto>,
)

@Serializable
data class ConsentAcceptBody(
    @SerialName("document_version") val documentVersion: String,
)

@Serializable
data class ConsentAcceptResponse(
    @SerialName("document_version") val documentVersion: String,
    @SerialName("accepted_at_epoch_millis") val acceptedAtEpochMillis: Long,
)
