#ifndef ASE_ENUMS_MQH
#define ASE_ENUMS_MQH
//+------------------------------------------------------------------+
//| ASE v3 — Core Enumerations                                       |\n//| Phase 2: Added ENUM_EXIT_REASON, REGIME_MANIPULATION             |
//| v3.13.0: Added ENUM_MACRO_REGIME for D1 ceiling classification.  |
//+------------------------------------------------------------------+

enum ENUM_ASE_STATE
{
   STATE_IDLE           = 0,
   STATE_WAIT_HTF       = 1,
   STATE_WAIT_SETUP     = 2,
   STATE_WAIT_TRIGGER   = 3,
   STATE_WAIT_EXECUTION = 4,
   STATE_POSITION_OPEN  = 5,
   STATE_MANAGE         = 6,
   STATE_COOLDOWN       = 7
};

enum ENUM_MARKET_REGIME
{
   REGIME_UNKNOWN       = 0,
   REGIME_TRENDING      = 1,
   REGIME_COMPRESSION   = 2,
   REGIME_HIGH_VOL      = 3,
   REGIME_DEAD          = 4,
   REGIME_MANIPULATION  = 5,  // high wick ratio — spec §7.1
   REGIME_RANGING       = 6   // v3.4.5: ATR expanded above compression but below trending
};

// v3.13.0 — D1 macro regime ceiling.
// Evaluated once per day at CheckDailyReset(). Acts as a ceiling gate
// on the H1 operational regime — can restrict but never promote.
//   MACRO_HIGH_VOL    → hard block regardless of H1 regime
//   MACRO_EXPANSION   → H1 runs freely; TRENDING allowed
//   MACRO_NEUTRAL     → H1 runs freely; all regimes allowed
//   MACRO_CONTRACTION → H1 TRENDING capped to RANGING
enum ENUM_MACRO_REGIME
{
   MACRO_UNKNOWN     = 0,
   MACRO_EXPANSION   = 1,  // D1 ATR > 1.2× 20-day average — directional expansion
   MACRO_NEUTRAL     = 2,  // D1 ATR within ±20% of 20-day average — normal conditions
   MACRO_CONTRACTION = 3,  // D1 ATR < 0.8× 20-day average — daily range contracting
   MACRO_HIGH_VOL    = 4   // D1 ATR > 1.8× 20-day average — hard block ceiling
};

enum ENUM_TRADE_DIRECTION
{
   DIR_NONE  = 0,
   DIR_LONG  = 1,
   DIR_SHORT = 2
};

// Trade close attribution — spec §2.1 exit_reason field
enum ENUM_EXIT_REASON
{
   EXIT_UNKNOWN      = 0,
   EXIT_SL           = 1,   // stopped out
   EXIT_TP1          = 2,   // partial close at TP1
   EXIT_TP2          = 3,   // full target hit
   EXIT_TRAIL        = 4,   // trailing stop
   EXIT_BREAKEVEN    = 5,   // closed at breakeven
   EXIT_MANUAL       = 6,   // closed externally
   EXIT_DD_HALT      = 7    // forced close by DD halt
};

// BOS/CHoCH structure type — used by StructureEngine
enum ENUM_STRUCTURE_TYPE
{
   STRUCT_NONE   = 0,
   STRUCT_BOS    = 1,   // Break of Structure (trend continuation)
   STRUCT_CHOCH  = 2    // Change of Character (potential reversal)
};
#endif // ASE_ENUMS_MQH
