package com.minimoney.app.data.child

import com.minimoney.app.domain.child.AgeBand
import com.minimoney.app.domain.child.ChildLinkRepository
import com.minimoney.app.domain.core.AppError
import com.minimoney.app.domain.core.AppResult
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.withContext
import retrofit2.HttpException
import java.io.IOException
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ChildLinkRepositoryImpl @Inject constructor(
    private val api: LinkChildApi,
    private val ioDispatcher: CoroutineDispatcher,
) : ChildLinkRepository {

    override suspend fun linkChild(email: String, displayName: String?, ageBand: AgeBand): AppResult<Unit> =
        withContext(ioDispatcher) {
            try {
                api.linkChild(LinkChildBody(email = email, displayName = displayName, ageBand = ageBand.name))
                AppResult.Success(Unit)
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
