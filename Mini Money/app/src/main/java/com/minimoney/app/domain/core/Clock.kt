package com.minimoney.app.domain.core

/** Injectable time source so time-dependent rules (SLA windows, timestamps) are testable. */
fun interface Clock {
    fun nowMillis(): Long
}
