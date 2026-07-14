package com.minimoney.app.domain.core

/** General-purpose failure taxonomy for non-auth features. */
sealed interface AppError {
    data object Network : AppError
    /** Server rejected the request because state moved underneath it (e.g. consent version changed). */
    data object Conflict : AppError
    data class Server(val httpCode: Int) : AppError
    data class Unknown(val cause: Throwable? = null) : AppError
}

sealed interface AppResult<out T> {
    data class Success<T>(val value: T) : AppResult<T>
    data class Failure(val error: AppError) : AppResult<Nothing>
}
