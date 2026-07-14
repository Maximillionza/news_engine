package com.minimoney.app.data.auth

import retrofit2.http.Body
import retrofit2.http.POST

/**
 * Parent auth endpoints. Phone + SMS-OTP only — there is no password, and no
 * child login exists independent of the parent account (BuildSpec §Data Model).
 */
interface AuthApi {

    @POST("v1/auth/otp/request")
    suspend fun requestOtp(@Body body: OtpRequestBody): OtpRequestResponse

    @POST("v1/auth/otp/verify")
    suspend fun verifyOtp(@Body body: OtpVerifyBody): OtpVerifyResponse
}
