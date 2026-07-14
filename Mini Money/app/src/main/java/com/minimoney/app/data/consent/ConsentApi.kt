package com.minimoney.app.data.consent

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST

interface ConsentApi {

    @GET("v1/consent/current")
    suspend fun getCurrentDocument(): ConsentDocumentDto

    /** Server rejects with 409 if the submitted version is no longer current. */
    @POST("v1/consent/accept")
    suspend fun acceptConsent(@Body body: ConsentAcceptBody): ConsentAcceptResponse
}
