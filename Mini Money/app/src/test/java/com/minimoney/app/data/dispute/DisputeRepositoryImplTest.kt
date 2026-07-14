package com.minimoney.app.data.dispute

import com.minimoney.app.data.db.DisputeDao
import com.minimoney.app.data.db.DisputeEntity
import com.minimoney.app.data.db.TaskDao
import com.minimoney.app.domain.core.AppResult
import com.minimoney.app.domain.core.Clock
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.mockk
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertTrue
import org.junit.Test

class DisputeRepositoryImplTest {

    private val disputeDao: DisputeDao = mockk(relaxed = true)
    private val taskDao: TaskDao = mockk(relaxed = true)

    private val hour = 60L * 60 * 1000

    private fun dispute(openedAt: Long, status: String = "OPEN") = DisputeEntity(
        id = 4, taskId = 7, childId = 1, openedAtMillis = openedAt, status = status,
    )

    @Test
    fun `escalation inside the 48h window is refused`() = runTest {
        val repo = DisputeRepositoryImpl(disputeDao, taskDao, Clock { 47 * hour })
        coEvery { disputeDao.get(4) } returns dispute(openedAt = 0)

        assertTrue(repo.escalate(4) is AppResult.Failure)
        coVerify(exactly = 0) { disputeDao.resolve(any(), any(), any()) }
    }

    @Test
    fun `escalation past the window moves to the founder-review queue`() = runTest {
        val repo = DisputeRepositoryImpl(disputeDao, taskDao, Clock { 49 * hour })
        coEvery { disputeDao.get(4) } returns dispute(openedAt = 0)

        assertTrue(repo.escalate(4) is AppResult.Success)
        coVerify { disputeDao.resolve(4, "ESCALATED", null) }
    }

    @Test
    fun `accept and decline only apply to OPEN disputes`() = runTest {
        val repo = DisputeRepositoryImpl(disputeDao, taskDao, Clock { hour })
        coEvery { disputeDao.get(4) } returns dispute(openedAt = 0, status = "ACCEPTED")

        assertTrue(repo.accept(4) is AppResult.Failure)
        assertTrue(repo.decline(4) is AppResult.Failure)
    }

    @Test
    fun `accept inside the window resolves with timestamp`() = runTest {
        val repo = DisputeRepositoryImpl(disputeDao, taskDao, Clock { hour })
        coEvery { disputeDao.get(4) } returns dispute(openedAt = 0)

        assertTrue(repo.accept(4) is AppResult.Success)
        coVerify { disputeDao.resolve(4, "ACCEPTED", hour) }
    }
}
