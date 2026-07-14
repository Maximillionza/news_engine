package com.minimoney.app.data.payslip

import com.minimoney.app.data.db.LatePenaltyEventEntity
import com.minimoney.app.data.db.LedgerDao
import com.minimoney.app.data.db.PaymentConfirmationEntity
import com.minimoney.app.data.db.PayslipDao
import com.minimoney.app.data.db.PayslipEntity
import com.minimoney.app.domain.core.AppError
import com.minimoney.app.domain.core.AppResult
import com.minimoney.app.domain.core.Clock
import com.minimoney.app.domain.payslip.LatePenaltyPolicy
import com.minimoney.app.domain.payslip.Payslip
import com.minimoney.app.domain.payslip.PayslipRepository
import com.minimoney.app.domain.payslip.PayslipStatus
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class PayslipRepositoryImpl @Inject constructor(
    private val payslipDao: PayslipDao,
    private val ledgerDao: LedgerDao,
    private val clock: Clock,
    @param:javax.inject.Named("is_pilot") private val isPilot: Boolean,
) : PayslipRepository {

    override fun payslipsFor(childId: Long): Flow<List<Payslip>> =
        payslipDao.withPenaltiesForChild(childId).map { list ->
            list.map {
                Payslip(
                    id = it.id,
                    childId = it.childId,
                    generatedAtMillis = it.generatedAtMillis,
                    earnedMbucks = it.earnedMbucks,
                    penaltyMbucks = it.penaltyMbucks,
                    status = PayslipStatus.valueOf(it.status),
                    paidConfirmedAtMillis = it.paidConfirmedAtMillis,
                )
            }
        }

    override suspend fun generate(childId: Long): AppResult<Long> {
        val entries = ledgerDao.uninvoicedFor(childId)
        if (entries.isEmpty()) return AppResult.Failure(AppError.Conflict)

        val payslipId = payslipDao.insert(
            PayslipEntity(
                childId = childId,
                generatedAtMillis = clock.nowMillis(),
                earnedMbucks = entries.sumOf { it.amountMbucks },
                status = PayslipStatus.GENERATED.name,
            ),
        )
        ledgerDao.attachToPayslip(entries.map { it.id }, payslipId)
        return AppResult.Success(payslipId)
    }

    override suspend fun confirmPaid(payslipId: Long): AppResult<Unit> {
        val payslip = payslipDao.get(payslipId) ?: return AppResult.Failure(AppError.Unknown())
        if (payslip.status == PayslipStatus.PAID.name) return AppResult.Failure(AppError.Conflict)
        val now = clock.nowMillis()
        payslipDao.setPaid(payslipId, PayslipStatus.PAID.name, now)
        payslipDao.insertConfirmation(
            PaymentConfirmationEntity(payslipId = payslipId, confirmedAtMillis = now),
        )
        return AppResult.Success(Unit)
    }

    override suspend fun applyLatePenalty(payslipId: Long, stepMbucks: Int): AppResult<Unit> {
        if (stepMbucks < 1) return AppResult.Failure(AppError.Unknown())
        val payslip = payslipDao.get(payslipId) ?: return AppResult.Failure(AppError.Unknown())
        if (payslip.status == PayslipStatus.PAID.name) return AppResult.Failure(AppError.Conflict)

        // Cap enforcement at the write level (BuildSpec §Data Model,
        // LatePenaltyEvent): 3 Mbucks pilot / 7 production. A step past the
        // cap is clamped to the remainder; at the cap, rejected outright.
        val cap = LatePenaltyPolicy.capMbucks(isPilot)
        val already = payslipDao.penaltyTotalFor(payslipId)
        val remaining = cap - already
        if (remaining <= 0) return AppResult.Failure(AppError.Conflict)

        payslipDao.insertPenalty(
            LatePenaltyEventEntity(
                payslipId = payslipId,
                amountMbucks = stepMbucks.coerceAtMost(remaining),
                appliedAtMillis = clock.nowMillis(),
            ),
        )
        return AppResult.Success(Unit)
    }
}
