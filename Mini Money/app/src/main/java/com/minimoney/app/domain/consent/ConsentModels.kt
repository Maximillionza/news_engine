package com.minimoney.app.domain.consent

data class ConsentSection(
    val title: String,
    val body: String,
)

/**
 * The consent text is server-sourced and versioned so it can change without
 * an app release; a version change forces re-consent (BuildSpec §Compliance,
 * POPIA s34/s35(1)(a)).
 */
data class ConsentDocument(
    val version: String,
    val sections: List<ConsentSection>,
)

data class ConsentAcceptance(
    val documentVersion: String,
    val acceptedAtEpochMillis: Long,
)
