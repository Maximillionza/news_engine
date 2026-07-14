package com.minimoney.app.presentation.home

import com.minimoney.app.MainDispatcherRule
import com.minimoney.app.domain.child.AgeBand
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

    private fun flags(linking: Boolean): FeatureFlags = mockk {
        every { accountLinkingEnabled } returns flowOf(linking)
        every { mpointsEnabled } returns flowOf(false)
    }

    @Test
    fun `linking entry hidden while flag off and shown when on - both launch configs`() = runTest {
        // OFF (launch configuration)
        val vmOff = HomeViewModel(repository, flags(linking = false))
        backgroundScope.launch { vmOff.accountLinkingEnabled.collect {} }
        runCurrent()
        assertFalse(vmOff.accountLinkingEnabled.value)

        // ON (post-recheck configuration)
        val vmOn = HomeViewModel(repository, flags(linking = true))
        backgroundScope.launch { vmOn.accountLinkingEnabled.collect {} }
        runCurrent()
        assertTrue(vmOn.accountLinkingEnabled.value)
    }

    @Test
    fun `add child submits and resets dialog on success`() = runTest {
        coEvery { repository.createChild("Nia", AgeBand.SIX_TO_NINE) } returns AppResult.Success(1L)
        val vm = HomeViewModel(repository, flags(false))

        vm.onShowAddChild()
        vm.onNameChanged("Nia")
        vm.onAgeBandSelected(AgeBand.SIX_TO_NINE)
        vm.onSubmitAddChild()
        runCurrent()

        coVerify(exactly = 1) { repository.createChild("Nia", AgeBand.SIX_TO_NINE) }
        assertFalse(vm.addChild.value.visible)
    }

    @Test
    fun `limit conflict surfaces in dialog`() = runTest {
        coEvery { repository.createChild(any(), any()) } returns AppResult.Failure(AppError.Conflict)
        val vm = HomeViewModel(repository, flags(false))

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
        val vm = HomeViewModel(repository, flags(false))
        vm.onShowAddChild()
        vm.onNameChanged("Nia")
        vm.onSubmitAddChild()
        runCurrent()
        coVerify(exactly = 0) { repository.createChild(any(), any()) }
    }
}
