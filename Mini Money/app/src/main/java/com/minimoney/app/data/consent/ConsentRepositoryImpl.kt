package com.minimoney.app.data.consent

import com.minimoney.app.data.auth.SessionStore
import com.minimoney.app.data.db.ConsentDao
import com.minimoney.app.data.db.ConsentRecordEntity
import com.minimoney.app.domain.consent.ConsentAcceptance
import com.minimoney.app.domain.consent.ConsentDocument
import com.minimoney.app.domain.consent.ConsentRepository
import com.minimoney.app.domain.consent.ConsentSection
import com.minimoney.app.domain.core.AppError
import com.minimoney.app.domain.core.AppResult
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.withContext
import retrofit2.HttpException
import java.io.IOException
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ConsentRepositoryImpl @Inject constructor(
    private val api: ConsentApi,
    private val consentDao: ConsentDao,
    private val sessionStore: SessionStore,
    private val ioDispatcher: CoroutineDispatcher,
) : ConsentRepository {

    override suspend fun getCurrentDocument(): AppResult<ConsentDocument> = safeCall {
        val dto = api.getCurrentDocument()
        ConsentDocument(
            version = dto.version,
            sections = dto.sections.map { ConsentSection(title = it.title, body = it.body) },
        )
    }

    override suspend fun acceptConsent(documentVersion: String): AppResult<ConsentAcceptance> {
        // Acceptance is meaningless without a verified session to attribute it to.
        val session = sessionStore.session.first()
            ?: return AppResult.Failure(AppError.Unknown())

        val result = safeCall {
            val resp = api.acceptConsent(ConsentAcceptBody(documentVersion))
            ConsentAcceptance(
                documentVersion = resp.documentVersion,
                acceptedAtEpochMillis = resp.acceptedAtEpochMillis,
            )
        }

        if (result is AppResult.Success) {
            // Server record is authoritative; the local row and session flag are
            // derived state. If a local write is lost, the server re-asserts
            // consent status at next sign-in.
            consentDao.insert(
                ConsentRecordEntity(
                    parentAccountId = session.parentAccountId,
                    documentVersion = result.value.documentVersion,
                    acceptedAtEpochMillis = result.value.acceptedAtEpochMillis,
                ),
            )
            sessionStore.markConsentComplete()
        }
        return result
    }

    private suspend fun <T> safeCall(block: suspend () -> T): AppResult<T> =
        withContext(ioDispatcher) {
            try {
                AppResult.Success(block())
            } catch (e: HttpException) {
                AppResult.Failure(
                    when (e.code()) {
                        409 -> AppError.Conflict
                        in 500..599 -> AppError.Server(e.code())
                        else -> AppError.Unknown(e)
                    },
                )
            } catch (e: IOException) {
                AppResult.Failure(AppError.Network)
            } catch (e: Exception) {
                AppResult.Failure(AppError.Unknown(e))
            }
        }
}
