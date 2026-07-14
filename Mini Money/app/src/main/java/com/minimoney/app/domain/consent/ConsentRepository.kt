package com.minimoney.app.domain.consent

import com.minimoney.app.domain.core.AppResult

interface ConsentRepository {

    suspend fun getCurrentDocument(): AppResult<ConsentDocument>

    /**
     * Records acceptance of the given document version: server-side
     * (authoritative), then the local versioned ConsentRecord, then flips the
     * session's consentComplete flag — which is what routes the parent into
     * the app.
     */
    suspend fun acceptConsent(documentVersion: String): AppResult<ConsentAcceptance>
}
