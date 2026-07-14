package com.minimoney.app.data.consent

import com.minimoney.app.data.auth.SessionStore
import com.minimoney.app.data.db.ConsentDao
import com.minimoney.app.data.db.ConsentRecordEntity
import com.minimoney.app.domain.auth.ParentSession
import com.minimoney.app.domain.core.AppError
import com.minimoney.app.domain.core.AppResult
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.every
import io.mockk.mockk
import io.mockk.slot
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.runTest
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import retrofit2.HttpException
import retrofit2.Response
import java.io.IOException

class ConsentRepositoryImplTest {

    private val api: ConsentApi = mockk()
    private val dao: ConsentDao = mockk(relaxed = true)
    private val accessLogger: com.minimoney.app.data.db.AccessLogger = mockk(relaxed = true)
    private val sessionStore: SessionStore = mockk(relaxed = true) {
        every { session } returns flowOf(ParentSession("acc-1", "tok", consentComplete = false))
    }

    private fun httpException(code: Int) = HttpException(
        Response.error<Any>(code, "{}".toResponseBody("application/json".toMediaType())),
    )

    @Test
    fun `accept success writes versioned local record and marks session`() = runTest {
        val repo = ConsentRepositoryImpl(api, dao, sessionStore, StandardTestDispatcher(testScheduler), accessLogger)
        coEvery { api.acceptConsent(ConsentAcceptBody("v1")) } returns
            ConsentAcceptResponse(documentVersion = "v1", acceptedAtEpochMillis = 1_720_000_000_000L)

        val result = repo.acceptConsent("v1")

        assertTrue(result is AppResult.Success)
        val record = slot<ConsentRecordEntity>()
        coVerify(exactly = 1) { dao.insert(capture(record)) }
        // The BuildSpec-required triple: version, timestamp, parent account id.
        assertEquals("v1", record.captured.documentVersion)
        assertEquals(1_720_000_000_000L, record.captured.acceptedAtEpochMillis)
        assertEquals("acc-1", record.captured.parentAccountId)
        coVerify(exactly = 1) { sessionStore.markConsentComplete() }
    }

    @Test
    fun `accept failure writes nothing and leaves session untouched`() = runTest {
        val repo = ConsentRepositoryImpl(api, dao, sessionStore, StandardTestDispatcher(testScheduler), accessLogger)
        coEvery { api.acceptConsent(any()) } throws httpException(500)

        val result = repo.acceptConsent("v1")

        assertEquals(AppResult.Failure(AppError.Server(500)), result)
        coVerify(exactly = 0) { dao.insert(any()) }
        coVerify(exactly = 0) { sessionStore.markConsentComplete() }
    }

    @Test
    fun `stale version maps to Conflict`() = runTest {
        val repo = ConsentRepositoryImpl(api, dao, sessionStore, StandardTestDispatcher(testScheduler), accessLogger)
        coEvery { api.acceptConsent(any()) } throws httpException(409)

        assertEquals(AppResult.Failure(AppError.Conflict), repo.acceptConsent("v0"))
    }

    @Test
    fun `accept without a session fails without any network call`() = runTest {
        val noSessionStore: SessionStore = mockk(relaxed = true) {
            every { session } returns flowOf(null)
        }
        val repo = ConsentRepositoryImpl(api, dao, noSessionStore, StandardTestDispatcher(testScheduler), accessLogger)

        val result = repo.acceptConsent("v1")

        assertTrue(result is AppResult.Failure)
        coVerify(exactly = 0) { api.acceptConsent(any()) }
    }

    @Test
    fun `document fetch maps DTO and IO failure to Network`() = runTest {
        val repo = ConsentRepositoryImpl(api, dao, sessionStore, StandardTestDispatcher(testScheduler), accessLogger)
        coEvery { api.getCurrentDocument() } returns ConsentDocumentDto(
            version = "v2",
            sections = listOf(ConsentSectionDto("Title", "Body")),
        )
        val success = repo.getCurrentDocument()
        assertTrue(success is AppResult.Success)
        assertEquals("v2", (success as AppResult.Success).value.version)
        assertEquals("Title", success.value.sections.single().title)

        coEvery { api.getCurrentDocument() } throws IOException("offline")
        assertEquals(AppResult.Failure(AppError.Network), repo.getCurrentDocument())
    }
}
