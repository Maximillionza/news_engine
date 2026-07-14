package com.minimoney.app.data.db

import androidx.room.ColumnInfo
import androidx.room.Dao
import androidx.room.Entity
import androidx.room.Insert
import androidx.room.PrimaryKey
import androidx.room.Query
import com.minimoney.app.domain.core.Clock
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Access log over the PII tables (ParentAccount-equivalent session data,
 * ChildProfile, ConsentRecord) — the technical half of the data-breach/
 * incident-response commitment (BuildSpec §Compliance): sufficient to detect
 * and evidence a breach event. Append-only; never exposed in any UI surface.
 *
 * NOTE: the commitment must not be represented as final policy until the
 * Data-Privacy Practitioner review has occurred (pre-pilot gate).
 */
@Entity(tableName = "access_log")
data class AccessLogEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "table_name") val tableName: String,
    @ColumnInfo(name = "row_ref") val rowRef: String?,
    @ColumnInfo(name = "action") val action: String,
    @ColumnInfo(name = "at") val atMillis: Long,
)

@Dao
interface AccessLogDao {
    @Insert
    suspend fun insert(entry: AccessLogEntity)

    @Query("SELECT COUNT(*) FROM access_log WHERE table_name = :tableName")
    suspend fun countFor(tableName: String): Int
}

enum class PiiAction { READ, WRITE, DELETE }

@Singleton
class AccessLogger @Inject constructor(
    private val dao: AccessLogDao,
    private val clock: Clock,
) {
    suspend fun log(tableName: String, action: PiiAction, rowRef: String? = null) {
        dao.insert(
            AccessLogEntity(
                tableName = tableName,
                rowRef = rowRef,
                action = action.name,
                atMillis = clock.nowMillis(),
            ),
        )
    }
}
