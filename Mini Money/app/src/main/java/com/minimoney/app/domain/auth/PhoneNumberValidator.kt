package com.minimoney.app.domain.auth

/**
 * South African mobile number validation and E.164 normalization.
 * Launch market is SA only (PRD §Product Summary), so +27 is the only
 * accepted country code; local format "0XXXXXXXXX" is normalized to it.
 */
object PhoneNumberValidator {

    sealed interface Result {
        /** Normalized E.164 form, e.g. +27821234567 */
        data class Valid(val phoneE164: String) : Result
        data object Invalid : Result
    }

    // SA mobile numbers: 9 digits after the leading 0 / country code,
    // first digit 6-8 (06x/07x/08x ranges).
    private val subscriberPattern = Regex("^[6-8]\\d{8}$")

    fun validate(raw: String): Result {
        val cleaned = raw.filterNot { it.isWhitespace() || it == '-' || it == '(' || it == ')' }
        val subscriber = when {
            cleaned.startsWith("+27") -> cleaned.removePrefix("+27")
            cleaned.startsWith("27") && cleaned.length == 11 -> cleaned.removePrefix("27")
            cleaned.startsWith("0") -> cleaned.removePrefix("0")
            else -> return Result.Invalid
        }
        return if (subscriberPattern.matches(subscriber)) {
            Result.Valid("+27$subscriber")
        } else {
            Result.Invalid
        }
    }
}
