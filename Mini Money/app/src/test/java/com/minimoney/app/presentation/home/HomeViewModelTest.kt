package com.minimoney.app.presentation.home

import com.minimoney.app.MainDispatcherRule
import com.minimoney.app.domain.child.AgeBand
import com.minimoney.app.domain.child.ChildLinkRepository
import com.minimoney.app.domain.child.ChildRepository
import com.minimoney.app.domain.core.AppError
import com.minimoney.app.domain.core.AppResult
import com.minimoney.app.domain.flags.FeatureFlags
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.every
import io.mockk.mockk
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class HomeViewModelTest {

    @get:Rule
    val mainDispatcherRule = MainDispatcherRule()

    private val repository: ChildRepository = mockk(relaxed = true) {
        every { children() } returns flowOf(emptyList())
    }
    private val linkRepository: ChildLinkRepository = mockk(relaxed = true)
    private val ledgerDao: com.minimoney.app.data.db.LedgerDao = mockk {
        every { mbucksPerChildSince(any()) } returns flowOf(emptyList())
    }
    private val taskDao: com.minimoney.app.data.db.TaskDao = mockk {
        every { pendingVerificationCounts() } returns flowOf(emptyList())
        every { forChild(any()) } returns flowOf(emptyList())
    }

    private fun flags(linking: Boolean): FeatureFlags = mockk {
        every { accountLinkingEnabled } returns flowOf(linking)
        every { mpointsEnabled } returns flowOf(false)
    }

    private fun viewModel(linking: Boolean = false) = HomeViewModel(
        repository, linkRepository, flags(linking), ledgerDao, taskDao,
        com.minimoney.app.domain.core.Clock { 0L },
    )

    @Test
    fun `linking entry hidden while flag off and shown when on - both launch configs`() = runTest {
        // OFF (launch configuration)
        val vmOff = viewModel(linking = false)
        backgroundScope.launch { vmOff.accountLinkingEnabled.collect {} }
        runCurrent()
        assertFalse(vmOff.accountLinkingEnabled.value)

        // ON (post-recheck configuration)
        val vmOn = viewModel(linking = true)
        backgroundScope.launch { vmOn.accountLinkingEnabled.collect {} }
        runCurrent()
        assertTrue(vmOn.accountLinkingEnabled.value)
    }

    @Test
    fun `add child with no email submits and resets dialog on success - Google linking untouched`() = runTest {
        coEvery { repository.createChild("Nia", AgeBand.SIX_TO_NINE) } returns AppResult.Success(1L)
        val vm = viewModel()

        vm.onShowAddChild()
        vm.onNameChanged("Nia")
        vm.onAgeBandSelected(AgeBand.SIX_TO_NINE)
        vm.onSubmitAddChild()
        runCurrent()

        coVerify(exactly = 1) { repository.createChild("Nia", AgeBand.SIX_TO_NINE) }
        coVerify(exactly = 0) { linkRepository.linkChild(any(), any(), any()) }
        assertFalse(vm.addChild.value.visible)
    }

    @Test
    fun `add child with an email also registers the Google link`() = runTest {
        coEvery { repository.createChild("Nia", AgeBand.SIX_TO_NINE) } returns AppResult.Success(1L)
        coEvery { linkRepository.linkChild("nia@example.com", "Nia", AgeBand.SIX_TO_NINE) } returns
            AppResult.Success(Unit)
        val vm = viewModel()

        vm.onShowAddChild()
        vm.onNameChanged("Nia")
        vm.onAgeBandSelected(AgeBand.SIX_TO_NINE)
        vm.onChildEmailChanged("nia@example.com")
        vm.onSubmitAddChild()
        runCurrent()

        coVerify(exactly = 1) { linkRepository.linkChild("nia@example.com", "Nia", AgeBand.SIX_TO_NINE) }
        assertFalse(vm.addChild.value.visible)
    }

    @Test
    fun `local profile still exists even if Google linking fails - dialog stays open with the link error`() = runTest {
        coEvery { repository.createChild("Nia", AgeBand.SIX_TO_NINE) } returns AppResult.Success(1L)
        coEvery { linkRepository.linkChild(any(), any(), any()) } returns AppResult.Failure(AppError.Network)
        val vm = viewModel()

        vm.onShowAddChild()
        vm.onNameChanged("Nia")
        vm.onAgeBandSelected(AgeBand.SIX_TO_NINE)
        vm.onChildEmailChanged("nia@example.com")
        vm.onSubmitAddChild()
        runCurrent()

        coVerify(exactly = 1) { repository.createChild("Nia", AgeBand.SIX_TO_NINE) } // local write still happened
        assertEquals(AppError.Network, vm.addChild.value.linkError)
        assertTrue(vm.addChild.value.visible)
    }

    @Test
    fun `limit conflict surfaces in dialog`() = runTest {
        coEvery { repository.createChild(any(), any()) } returns AppResult.Failure(AppError.Conflict)
        val vm = viewModel()

        vm.onShowAddChild()
        vm.onNameChanged("Nia")
        vm.onAgeBandSelected(AgeBand.SIX_TO_NINE)
        vm.onSubmitAddChild()
        runCurrent()

        assertEquals(AppError.Conflict, vm.addChild.value.error)
        assertTrue(vm.addChild.value.visible)
    }

    @Test
    fun `submit without age band is inert`() = runTest {
        val vm = viewModel()
        vm.onShowAddChild()
        vm.onNameChanged("Nia")
        vm.onSubmitAddChild()
        runCurrent()
        coVerify(exactly = 0) { repository.createChild(any(), any()) }
    }
}
