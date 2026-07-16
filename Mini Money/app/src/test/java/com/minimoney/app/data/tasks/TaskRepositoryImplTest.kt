package com.minimoney.app.data.tasks

import com.minimoney.app.data.db.ChildDao
import com.minimoney.app.data.db.ChildProfileEntity
import com.minimoney.app.data.db.LedgerDao
import com.minimoney.app.data.db.MbuckLedgerEntryEntity
import com.minimoney.app.data.db.TaskDao
import com.minimoney.app.data.db.TaskEntity
import com.minimoney.app.domain.core.AppResult
import com.minimoney.app.domain.core.Clock
import com.minimoney.app.domain.flags.FeatureFlags
import com.minimoney.app.domain.tasks.EarnMode
import com.minimoney.app.domain.tasks.Frequency
import com.minimoney.app.domain.tasks.TaskRepository
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.every
import io.mockk.mockk
import io.mockk.slot
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class TaskRepositoryImplTest {

    private val taskDao: TaskDao = mockk(relaxed = true)
    private val childDao: ChildDao = mockk()
    private val ledgerDao: LedgerDao = mockk(relaxed = true)
    private val flagsOff: FeatureFlags = mockk {
        every { mpointsEnabled } returns flowOf(false)
    }
    private val clock = Clock { 1_000L }

    // Interface-typed so callers below use TaskRepository's default frequency
    // argument (Kotlin overrides can't redeclare defaults on their own).
    private fun repo(flags: FeatureFlags = flagsOff): TaskRepository =
        TaskRepositoryImpl(taskDao, childDao, ledgerDao, flags, clock)

    private fun child(budget: Int?) = ChildProfileEntity(
        id = 1, parentAccountId = "acc-1", displayName = "T",
        ageBand = "TEN_TO_FOURTEEN", budgetRand = budget, createdAtMillis = 0,
    )

    private fun task(status: String, mbuckValue: Int = 5) = TaskEntity(
        id = 7, childId = 1, title = "Dishes", earnMode = "FIXED",
        earnValue = mbuckValue, mbuckValue = mbuckValue, status = status, createdAtMillis = 0,
    )

    @Test
    fun `fixed mode zero is rejected at input - not floored`() = runTest {
        coEvery { childDao.get(1) } returns child(budget = 100)
        val result = repo().createTask(1, "Dishes", EarnMode.FIXED, 0)
        assertTrue(result is AppResult.Failure)
        coVerify(exactly = 0) { taskDao.insert(any()) }
    }

    @Test
    fun `percentage mode snapshots truncated value from current budget`() = runTest {
        coEvery { childDao.get(1) } returns child(budget = 199)
        coEvery { taskDao.insert(any()) } returns 9L

        repo().createTask(1, "Dishes", EarnMode.PERCENTAGE, 1) // 1.99 -> 1

        val inserted = slot<TaskEntity>()
        coVerify { taskDao.insert(capture(inserted)) }
        assertEquals(1, inserted.captured.mbuckValue)
        assertEquals(1, inserted.captured.earnValue) // percent kept for audit
    }

    @Test
    fun `percentage mode floors a zero truncation to 1 Mbuck`() = runTest {
        coEvery { childDao.get(1) } returns child(budget = 50)
        coEvery { taskDao.insert(any()) } returns 9L

        repo().createTask(1, "Dishes", EarnMode.PERCENTAGE, 1) // 0.5 -> 0 -> 1

        val inserted = slot<TaskEntity>()
        coVerify { taskDao.insert(capture(inserted)) }
        assertEquals(1, inserted.captured.mbuckValue)
    }

    @Test
    fun `percentage mode without a budget set fails`() = runTest {
        coEvery { childDao.get(1) } returns child(budget = null)
        assertTrue(repo().createTask(1, "Dishes", EarnMode.PERCENTAGE, 5) is AppResult.Failure)
    }

    @Test
    fun `daily frequency divides the percentage total across 30 occurrences and persists the frequency`() = runTest {
        coEvery { childDao.get(1) } returns child(budget = 3000)
        coEvery { taskDao.insert(any()) } returns 9L

        repo().createTask(1, "Dishes", EarnMode.PERCENTAGE, 30, Frequency.DAILY) // 30% of 3000 = 900 / 30 = 30

        val inserted = slot<TaskEntity>()
        coVerify { taskDao.insert(capture(inserted)) }
        assertEquals(30, inserted.captured.mbuckValue)
        assertEquals("DAILY", inserted.captured.frequency)
    }

    @Test
    fun `weekly frequency divides the fixed total across the 4point3 occurrence assumption`() = runTest {
        coEvery { childDao.get(1) } returns child(budget = 100)
        coEvery { taskDao.insert(any()) } returns 9L

        repo().createTask(1, "Dishes", EarnMode.FIXED, 100, Frequency.WEEKLY) // 100 / 4.3 = 23.25... -> 23

        val inserted = slot<TaskEntity>()
        coVerify { taskDao.insert(capture(inserted)) }
        assertEquals(23, inserted.captured.mbuckValue)
        assertEquals("WEEKLY", inserted.captured.frequency)
    }

    @Test
    fun `tier mode snapshots the weighted share using the current template catalog`() = runTest {
        coEvery { childDao.get(1) } returns child(budget = 3000) // ageBand = TEN_TO_FOURTEEN
        coEvery { taskDao.insert(any()) } returns 9L

        // "Homework completed on time": weight 5 of daily-tier totalWeight 10, 40% tier share.
        // 40% of 3000 = 1200; 1200 * 5/10 = 600; / 30 daily occurrences = 20.
        repo().createTask(1, "Homework completed on time", EarnMode.TIER, 5, Frequency.DAILY)

        val inserted = slot<TaskEntity>()
        coVerify { taskDao.insert(capture(inserted)) }
        assertEquals(20, inserted.captured.mbuckValue)
        assertEquals(5, inserted.captured.earnValue) // relative weight kept for audit
        assertEquals("TIER", inserted.captured.earnMode)
    }

    @Test
    fun `tier mode without a budget set fails`() = runTest {
        coEvery { childDao.get(1) } returns child(budget = null)
        assertTrue(repo().createTask(1, "Homework completed on time", EarnMode.TIER, 5, Frequency.DAILY) is AppResult.Failure)
    }

    @Test
    fun `tier mode rejects a weight exceeding the age band's tier total`() = runTest {
        coEvery { childDao.get(1) } returns child(budget = 3000) // daily-tier totalWeight for this band is 10
        assertTrue(repo().createTask(1, "Made up", EarnMode.TIER, 999, Frequency.DAILY) is AppResult.Failure)
        coVerify(exactly = 0) { taskDao.insert(any()) }
    }

    @Test
    fun `omitted frequency defaults to monthly - unchanged one-off behavior`() = runTest {
        coEvery { childDao.get(1) } returns child(budget = 100)
        coEvery { taskDao.insert(any()) } returns 9L

        repo().createTask(1, "Dishes", EarnMode.FIXED, 100)

        val inserted = slot<TaskEntity>()
        coVerify { taskDao.insert(capture(inserted)) }
        assertEquals(100, inserted.captured.mbuckValue)
        assertEquals("MONTHLY", inserted.captured.frequency)
    }

    @Test
    fun `verify writes the Mbuck earning and no Mpoints while flag is off`() = runTest {
        coEvery { taskDao.get(7) } returns task(status = "COMPLETED")

        repo().verify(7)

        val entry = slot<MbuckLedgerEntryEntity>()
        coVerify(exactly = 1) { ledgerDao.insertMbuck(capture(entry)) }
        assertEquals(5, entry.captured.amountMbucks)
        coVerify(exactly = 0) { ledgerDao.insertMpoint(any()) }
    }

    @Test
    fun `verify writes flat 10 Mpoints when flag is on`() = runTest {
        val flagsOn: FeatureFlags = mockk { every { mpointsEnabled } returns flowOf(true) }
        coEvery { taskDao.get(7) } returns task(status = "COMPLETED")

        repo(flagsOn).verify(7)

        coVerify(exactly = 1) {
            ledgerDao.insertMpoint(match { it.amountMpoints == MPOINTS_PER_TASK })
        }
    }

    @Test
    fun `verify requires COMPLETED status`() = runTest {
        coEvery { taskDao.get(7) } returns task(status = "ASSIGNED")
        assertTrue(repo().verify(7) is AppResult.Failure)
        coVerify(exactly = 0) { ledgerDao.insertMbuck(any()) }
    }

    @Test
    fun `completion only moves ASSIGNED tasks`() = runTest {
        coEvery { taskDao.get(7) } returns task(status = "VERIFIED")
        assertTrue(repo().markCompleted(7) is AppResult.Failure)
    }
}
