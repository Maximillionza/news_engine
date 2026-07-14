package com.minimoney.app.data.payslip

import com.minimoney.app.data.db.LatePenaltyEventEntity
import com.minimoney.app.data.db.LedgerDao
import com.minimoney.app.data.db.MbuckLedgerEntryEntity
import com.minimoney.app.data.db.PayslipDao
import com.minimoney.app.data.db.PayslipEntity
import com.minimoney.app.domain.core.AppError
import com.minimoney.app.domain.core.AppResult
import com.minimoney.app.domain.core.Clock
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.mockk
import io.mockk.slot
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class PayslipRepositoryImplTest {

    private val payslipDao: PayslipDao = mockk(relaxed = true)
    private val ledgerDao: LedgerDao = mockk(relaxed = true)
    private val clock = Clock { 5_000L }

    private fun pilotRepo() = PayslipRepositoryImpl(payslipDao, ledgerDao, clock, true)
    private fun productionRepo() = PayslipRepositoryImpl(payslipDao, ledgerDao, clock, false)

    private fun payslip(status: String = "GENERATED") = PayslipEntity(
        id = 3, childId = 1, generatedAtMillis = 0, earnedMbucks = 20, status = status,
    )

    private fun entry(id: Long, amount: Int) = MbuckLedgerEntryEntity(
        id = id, childId = 1, taskId = id, amountMbucks = amount, earnedAtMillis = 0,
    )

    @Test
    fun `generate sums uninvoiced entries and attaches them`() = runTest {
        coEvery { ledgerDao.uninvoicedFor(1) } returns listOf(entry(1, 5), entry(2, 7))
        coEvery { payslipDao.insert(any()) } returns 3L

        val result = pilotRepo().generate(1)

        assertTrue(result is AppResult.Success)
        val inserted = slot<PayslipEntity>()
        coVerify { payslipDao.insert(capture(inserted)) }
        assertEquals(12, inserted.captured.earnedMbucks)
        coVerify { ledgerDao.attachToPayslip(listOf(1L, 2L), 3L) }
    }

    @Test
    fun `generate with nothing to invoice fails`() = runTest {
        coEvery { ledgerDao.uninvoicedFor(1) } returns emptyList()
        assertTrue(pilotRepo().generate(1) is AppResult.Failure)
        coVerify(exactly = 0) { payslipDao.insert(any()) }
    }

    @Test
    fun `pilot cap - step past 3 Mbucks is clamped to the remainder`() = runTest {
        coEvery { payslipDao.get(3) } returns payslip()
        coEvery { payslipDao.penaltyTotalFor(3) } returns 2 // 1 Mbuck of headroom

        pilotRepo().applyLatePenalty(3, 2)

        val event = slot<LatePenaltyEventEntity>()
        coVerify { payslipDao.insertPenalty(capture(event)) }
        assertEquals(1, event.captured.amountMbucks) // clamped, total never exceeds 3
    }

    @Test
    fun `pilot cap - at 3 Mbucks any further step is rejected`() = runTest {
        coEvery { payslipDao.get(3) } returns payslip()
        coEvery { payslipDao.penaltyTotalFor(3) } returns 3

        assertEquals(
            AppResult.Failure(AppError.Conflict),
            pilotRepo().applyLatePenalty(3, 1),
        )
        coVerify(exactly = 0) { payslipDao.insertPenalty(any()) }
    }

    @Test
    fun `production cap is 7 Mbucks`() = runTest {
        coEvery { payslipDao.get(3) } returns payslip()
        coEvery { payslipDao.penaltyTotalFor(3) } returns 6

        productionRepo().applyLatePenalty(3, 5)

        val event = slot<LatePenaltyEventEntity>()
        coVerify { payslipDao.insertPenalty(capture(event)) }
        assertEquals(1, event.captured.amountMbucks)
    }

    @Test
    fun `no penalty can be applied to a paid payslip`() = runTest {
        coEvery { payslipDao.get(3) } returns payslip(status = "PAID")
        assertTrue(pilotRepo().applyLatePenalty(3, 1) is AppResult.Failure)
    }

    @Test
    fun `confirmPaid records confirmation once and only once`() = runTest {
        coEvery { payslipDao.get(3) } returns payslip()
        assertTrue(pilotRepo().confirmPaid(3) is AppResult.Success)
        coVerify(exactly = 1) { payslipDao.insertConfirmation(match { it.payslipId == 3L }) }

        coEvery { payslipDao.get(3) } returns payslip(status = "PAID")
        assertTrue(pilotRepo().confirmPaid(3) is AppResult.Failure)
    }
}
