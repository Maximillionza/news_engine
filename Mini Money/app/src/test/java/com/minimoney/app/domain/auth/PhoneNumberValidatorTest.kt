package com.minimoney.app.domain.auth

import org.junit.Assert.assertEquals
import org.junit.Test

class PhoneNumberValidatorTest {

    private fun valid(raw: String, expected: String) =
        assertEquals(PhoneNumberValidator.Result.Valid(expected), PhoneNumberValidator.validate(raw))

    private fun invalid(raw: String) =
        assertEquals(PhoneNumberValidator.Result.Invalid, PhoneNumberValidator.validate(raw))

    @Test fun `local format normalizes to E164`() = valid("0821234567", "+27821234567")
    @Test fun `E164 input passes through`() = valid("+27821234567", "+27821234567")
    @Test fun `country code without plus accepted`() = valid("27821234567", "+27821234567")
    @Test fun `spaces and dashes stripped`() = valid("082 123-4567", "+27821234567")

    @Test fun `landline prefix rejected`() = invalid("0211234567")
    @Test fun `too short rejected`() = invalid("082123456")
    @Test fun `too long rejected`() = invalid("08212345678")
    @Test fun `foreign country code rejected`() = invalid("+44821234567")
    @Test fun `empty rejected`() = invalid("")
    @Test fun `letters rejected`() = invalid("08212345ab")
}
