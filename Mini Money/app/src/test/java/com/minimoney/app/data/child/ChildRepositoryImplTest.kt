package com.minimoney.app.data.child

import com.minimoney.app.data.auth.SessionStore
import com.minimoney.app.data.db.ChildDao
import com.minimoney.app.domain.auth.ParentSession
import com.minimoney.app.domain.child.AgeBand
import com.minimoney.app.domain.core.AppResult
import com.minimoney.app.domain.core.Clock
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.every
import io.mockk.mockk
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertTrue
import org.junit.Test

class ChildRepositoryImplTest {

    private val childDao: ChildDao = mockk(relaxed = true)
    private val sessionStore: SessionStore = mockk {
        every { session } returns flowOf(ParentSession("acc-1", "tok", true))
    }

    private fun repo() = ChildRepositoryImpl(childDao, sessionStore, Clock { 0L })

    @Test
    fun `fifth child is refused - 4 per parent enforced at write`() = runTest {
        coEvery { childDao.countFor("acc-1") } returns 4
        assertTrue(repo().createChild("Nia", AgeBand.SIX_TO_NINE) is AppResult.Failure)
        coVerify(exactly = 0) { childDao.insert(any()) }
    }

    @Test
    fun `fourth child is allowed`() = runTest {
        coEvery { childDao.countFor("acc-1") } returns 3
        coEvery { childDao.insert(any()) } returns 4L
        assertTrue(repo().createChild("Nia", AgeBand.SIX_TO_NINE) is AppResult.Success)
    }

    @Test
    fun `budget must be a positive whole Rand`() = runTest {
        assertTrue(repo().setBudget(1, 0) is AppResult.Failure)
        assertTrue(repo().setBudget(1, -5) is AppResult.Failure)
        coVerify(exactly = 0) { childDao.setBudget(any(), any()) }
    }
}
