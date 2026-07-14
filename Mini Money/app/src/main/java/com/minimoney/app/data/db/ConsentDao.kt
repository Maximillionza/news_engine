package com.minimoney.app.data.db

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query

@Dao
interface ConsentDao {

    @Insert
    suspend fun insert(record: ConsentRecordEntity)

    @Query(
        "SELECT * FROM consent_records WHERE parent_account_id = :parentAccountId " +
            "ORDER BY accepted_at_epoch_millis DESC LIMIT 1",
    )
    suspend fun latestFor(parentAccountId: String): ConsentRecordEntity?
}
