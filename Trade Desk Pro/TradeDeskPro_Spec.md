# Trade Desk Pro — Cowork Build Specification

**Version:** 1.0.0  
**Magic Number:** 999999  
**File Prefix:** `TDP_`  
**Platform:** MetaTrader 5  
**EA Type:** Non-trading shell with CTrade execution and full on-chart panel  

---

## Decisions Log (All Locked)

| Decision | Value |
|---|---|
| Tool name | Trade Desk Pro |
| Magic number | 999999 |
| File prefix | TDP_ |
| Lot sizing default | Risk-Based, toggle in Settings |
| Risk distribution default | Per Trade, toggle in Settings |
| Max trades in planner | 10 |
| ATR slippage buffer | H1 ATR(14) × 0.1 multiplier (user-overridable in Settings) |
| Trail stop implementation | MT5 native |
| Panel theme default | Light |
| Pending order expiry | Optional input field |
| Close-in-profit threshold | 1.0% default, user-overridable in Settings |
| Global scope | All trades regardless of origin or magic number |

---

## File Structure

```
TradeDeskPro.mq5      — EA shell: OnInit, OnDeinit, OnTick, OnChartEvent
TDP_Panel.mqh         — Wrapper class: all panel construction and event routing
TDP_Planner.mqh       — Lot engine, validation, order placement
TDP_Manager.mqh       — Trade list, modify logic, close logic, profit watcher
TDP_Settings.mqh      — Settings overlay, GlobalVariable persistence
TDP_Utils.mqh         — ATR fetch, tick value calc, spread, symbol info helpers
```

---

## Module 1 — Trade Planner (`[PLAN]` tab)

### Trade Count

- Integer input, range 1–10
- Label updates dynamically: `1 Trade` / `5 Trades`

### Risk Distribution

Visible only when trade count > 1.

Toggle: **Per Trade** (default) | **Split**

- **Per Trade** — risk input applies independently to each trade. Total exposure = N × risk amount.
- **Split** — risk input is divided equally across N trades. Total exposure = risk input.

When N > 1, display a **Combined Risk** summary line beneath all trade cards showing total dollar risk and total margin required.

### Lot Sizing Engine

Settings-level toggle: **Risk-Based** (default) | **Fixed**

**Risk-Based sub-toggle:** `% of Balance` | `$ Amount`

Formula:
```
Lot = Risk Amount ÷ (SL distance in points × tick value per lot)
```

**Fixed:** manual lot input, clamped to broker min/max/step on every keystroke.

Lot size displayed per trade card and recalculates live as SL or risk inputs change.

### Entry Mode

Toggle: **Immediate** | **Pending**

- **Immediate** — market order at current ask/bid.
- **Pending** — user inputs entry price.
  - `Entry > current ask` → Buy Stop
  - `Entry < current bid` → Sell Stop
  - Entry within spread zone → yellow warning label, require explicit confirmation before placement
- **Expiry field** (Pending only, optional) — datetime picker, defaults empty. If left empty, order has no expiry.

### SL / TP Inputs

Shared unit toggle for both SL and TP: **Points** | **Pips** | **% of Price** | **$ Amount**

- SL is required when lot mode is Risk-Based — validate and surface error if absent.
- TP is optional — profit fields show `—` if absent.
- All values convert internally to points for order submission.

### Per-Trade Display Card

One card rendered per planned trade (1–10 cards, scrollable if needed):

```
Trade #1                              [BUY STOP]
Entry:    1,234.50
Lot:      0.20
SL:       1,220.00   (-145 pts)   Risk:    $29.00
TP:       1,260.00   (+255 pts)   Profit:  $51.00
R:R  1 : 1.76        Margin req:  $220.00
```

Values recalculate live on every input change.

Combined totals row at bottom when N > 1:

```
─────────────────────────────────────────────────
5 Trades    Total Risk: $145.00    Margin: $1,100.00
```

### Pre-Flight Validation

Fires on `Place Orders` button. Runs sequentially — blocks placement and displays a specific error if any check fails.

1. Margin sufficiency — combined margin across all N trades vs free margin
2. Market open / symbol trading hours
3. Broker minimum stop distance (`SYMBOL_TRADE_STOPS_LEVEL`) per trade
4. Lot within broker min/max/step per trade
5. Spread-zone entry warning confirmation (Pending mode only)
6. SL present when Risk-Based lot mode is active

---

## Module 2 — Trade Manager (`[MANAGE]` tab)

### Availability

- Tab always visible.
- Empty state when no trades are open: `"No active trades detected"`
- Auto-populates when any trade opens on the terminal, regardless of origin or magic number.

### Scope Toggle

`Global` → `Chart` → `Selected`

- **Global** — all open trades across all symbols and all magic numbers.
- **Chart** — all open trades on the symbol the EA is currently attached to.
- **Selected** — user checks individual tickets from the trade list. All actions apply only to checked rows.

### Trade List

Scrollable table, one row per ticket:

```
[✓] #12345  XAUUSD  BUY   0.20   Entry: 1,234.50  Now: 1,241.00   SL: 1,220.00  TP: 1,260.00   +$13.20 (+0.46%)  [EXT]
```

**Columns:** Checkbox (Selected scope), ticket, symbol, direction, lot, entry price, current price, SL, TP, floating P&L ($), floating P&L (%), origin tag.

**Origin tag:** `TDP` for own magic number (999999), `EXT` for all other origins.

**P&L colouring:** Green for positive, red for negative.

**Sort:** Default by open time descending. Tap column header to re-sort.

### Modify SL / TP

- Unit toggle: **Points** | **Pips** | **% of Price** | **$ Amount**
- Apply mode toggle: **Absolute Price** | **Relative Offset (±N points)**
- Scope-aware — modifies all trades in active scope.
- **Breakeven button** — sets SL to `entry price ± spread` for all trades in scope, direction-aware.
- **Trail Arm button** — input field for trail distance in points, arms MT5 native trailing stop for all trades in scope.

### Close Operations

All close operations respect active scope.

#### Close All
- Single confirmation dialog.
- Immediate market close of all trades in scope.

#### Close All in Profit

Per-trade evaluation runs on every tick:

1. Compute `breakeven_price = entry ± (spread + ATR_buffer)` where `ATR_buffer = H1_ATR(14) × 0.1`
2. If `floating_profit% ≥ threshold (default 1.0%)` → close immediately
3. If trade is in profit but below threshold → arm watcher, close when threshold is crossed
4. If trade is at a loss → skip entirely, do not watch

Watcher state persists in `GlobalVariables` across chart reattach.

Active watchers shown as badge on the button: `Close in Profit (3 watching)`

#### Close All in Loss
- Double confirmation dialog:
  - First: `"This will close all losing trades. Are you sure?"`
  - Second: `"Confirm — this cannot be undone"`
- Immediate close of all trades in scope where `floating_profit < 0`.

#### Close Oldest N
- Integer input for N.
- Closes the N oldest open trades in scope by open time, ascending.
- Useful for position triage when a session deteriorates.

#### Close Largest Loss
- Closes the single trade with the worst current P&L in scope.
- Repeat-tappable — each tap closes the next worst.

### Panel Header (always visible, both tabs)

```
Equity: $10,432.00    Margin Level: 312%    Open: 5 trades    Float P&L: +$47.20
Largest drawdown (scope): -$18.40
```

---

## Module 3 — Settings Panel

Accessible via gear icon (`⚙`) — overlay on top of main panel.

| Setting | Default | Options |
|---|---|---|
| Lot sizing mode | Risk-Based | Risk-Based / Fixed |
| Risk distribution | Per Trade | Per Trade / Split |
| Default risk % | 1.0% | User input |
| ATR slippage multiplier | 0.1 | User input |
| Close-in-profit threshold | 1.0% | User input |
| Panel corner anchor | Top-Right | TL / TR / BL / BR |
| Panel colour theme | Light | Light / Dark |
| Collapse on trade placement | No | Yes / No |

All settings persisted to `GlobalVariables` with prefix `TDP_SETTING_`.

---

## Technical Notes for Build

### ATR Slippage Buffer
```
ATR_buffer = iATR(symbol, PERIOD_H1, 14, 1) × multiplier
```
Applied directionally: added to entry for long breakeven, subtracted for short breakeven.

### Profit Watcher Loop
Runs inside `OnTick`. Iterates all armed trades stored in GlobalVariables. On terminal restart, watcher re-arms from persisted state automatically on next `OnInit`.

### Panel Framework
Lightweight wrapper class `TDP_Panel.mqh` handles all object creation, event routing, and theme application. No raw object calls outside this class. Consistent with ACE DisplayPanel pattern.

### Magic Number Handling
- Trades placed by Trade Desk Pro use magic number `999999`.
- The Manager reads and acts on **all** trades regardless of magic number.
- Origin tag in trade list is display-only and does not restrict any management action.

### Version Bumping
On each version increment, update the version string in the EA header comment. Magic number `999999` is fixed and does not change with version.
