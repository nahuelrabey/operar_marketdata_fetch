# Desktop Interface Wireframe (Tkinter)

This document describes the visual layout and widget structure for the Market Data Desktop Application.

## Main Window
- **Title**: "Market Data Manager"
- **Geometry**: 1024x768
- **Layout**: `ttk.Notebook` (Tabs)

---

## Tab 1: Login
**Goal**: Authenticate with Invertir Online.

```
+--------------------------------------------------------------------------+
|  [ Tab: Login ] [ Tab: Market Data ] [ Tab: Prices ] [ Tab: Strategies ] |
+--------------------------------------------------------------------------+
|                                                                          |
|   +-------------------------------------------------------+              |
|   |  Authentication                                       |              |
|   +-------------------------------------------------------+              |
|   |                                                       |              |
|   |   Username: [ _______________ ]                       |              |
|   |                                                       |              |
|   |   Password: [ *************** ]                       |              |
|   |                                                       |              |
|   |   [ Login Button ]                                    |              |
|   |                                                       |              |
|   +-------------------------------------------------------+              |
|                                                                          |
|   +-------------------------------------------------------+              |
|   |  Status                                               |              |
|   +-------------------------------------------------------+              |
|   |                                                       |              |
|   |   Token: [ (Hidden/Displayed after login) ]           |              |
|   |   Status: "Not Logged In" / "Login Successful"        |              |
|   |                                                       |              |
|   +-------------------------------------------------------+              |
|                                                                          |
+--------------------------------------------------------------------------+
```

**Widgets**:
- `lbl_username`, `entry_username`
- `lbl_password`, `entry_password` (show="*")
- `btn_login` (Command: `login.authenticate`)
- `lbl_status` (Updates with result)
- `entry_token` (ReadOnly, populates on success)

---

## Tab 2: Market Data
**Goal**: Fetch and store option chains.

```
+--------------------------------------------------------------------------+
|  [ Tab: Login ] [ Tab: Market Data ] [ Tab: Prices ] [ Tab: Strategies ] |
+--------------------------------------------------------------------------+
|                                                                          |
|   +-------------------------------------------------------+              |
|   |  Fetch Options Data                                   |              |
|   +-------------------------------------------------------+              |
|   |                                                       |              |
|   |   Underlying Symbol: [ GGAL         ]                 |              |
|   |                                                       |              |
|   |   [ Fetch Data Button ]                               |              |
|   |                                                       |              |
|   +-------------------------------------------------------+              |
|                                                                          |
|   +-------------------------------------------------------+              |
|   |  Logs / Output                                        |              |
|   +-------------------------------------------------------+              |
|   |                                                       |              |
|   |   [Text Area / ScrolledText]                          |              |
|   |   > Fetching GGAL...                                  |              |
|   |   > Received 150 contracts.                           |              |
|   |   > Saved to database.                                |              |
|   |                                                       |              |
|   +-------------------------------------------------------+              |
|                                                                          |
+--------------------------------------------------------------------------+
```

**Widgets**:
- `lbl_symbol`, `entry_symbol` (Default: "GGAL")
- `btn_fetch` (Command: `fetch_data.fetch_option_chain` -> `database.upsert...`)
- `txt_log` (Displays progress messages)

---

## Tab 3: Current Prices
**Goal**: View latest prices for an underlying.

```
+--------------------------------------------------------------------------+
|  [ Tab: Login ] [ Tab: Market Data ] [ Tab: Prices ] [ Tab: Strategies ] |
+--------------------------------------------------------------------------+
|                                                                          |
|   Underlying: [ GGAL         ] [ Search Button ]                         |
|                                                                          |
|   +------------------------------------------------------------------+   |
|   | Symbol    | Type | Strike  | Last | Time                         |   |
|   | GGALC2600 | Call | 2600.00 | 10.5 | 2025-12-04 10:30:00          |   |
|   | GGALV2600 | Put  | 2600.00 | 5.2  | 2025-12-04 10:31:00          |   |
|   +------------------------------------------------------------------+   |
|                                                                          |
+--------------------------------------------------------------------------+
```

**Widgets**:
- `entry_search_symbol`
- `btn_search` (Command: `database.get_latest_prices_by_underlying`)
- `tree_prices`: Columns ("Symbol", "Type", "Strike", "Last", "Time")

---

## Tab 4: Strategies (Portfolio)
**Goal**: Manage positions and view P&L.

**Layout**: Split View (Left: List, Right: Details)

```
+--------------------------------------------------------------------------+
|  [ Tab: Login ] [ Tab: Market Data ] [ Tab: Prices ] [ Tab: Strategies ] |
+--------------------------------------------------------------------------+
|                                                                          |
|  +-------------------+  +----------------------------------+             |
|  | Strategy List     |  | Strategy Details                 |             |
|  +-------------------+  +----------------------------------+             |
|  |                   |  |                                  |             |
|  | [ Listbox/Tree ]  |  |  Name: Bull Spread GGAL          |             |
|  |                   |  |  Status: OPEN                    |             |
|  | - Bull Spread     |  |  Current P&L: $ 15,400.00        |             |
|  | - Iron Condor     |  |                                  |             |
|  | - Long Call       |  |  [ Close Strategy Button ]       |             |
|  |                   |  |                                  |             |
|  |                   |  |  +----------------------------+  |             |
|  |                   |  |  | Composition (Treeview)     |  |             |
|  |                   |  |  +----------------------------+  |             |
|  |                   |  |  | Symbol      | Net Qty      |  |             |
|  |                   |  |  | GGALC2600   | +10          |  |             |
|  |                   |  |  | GGALC2800   | -10          |  |             |
|  |                   |  |  +----------------------------+  |             |
|  |                   |  |                                  |             |
|  |                   |  |  +----------------------------+  |             |
|  |                   |  |  | P&L Graph (Canvas)         |  |             |
|  |                   |  |  |                            |  |             |
|  |                   |  |  |      /                     |  |             |
|  |                   |  |  |    _/                      |  |             |
|  |                   |  |  | __/                        |  |             |
|  |                   |  |  +----------------------------+  |             |
|  |                   |  |                                  |             |
|  | [ New Strategy ]  |  |  [ Add Trade Button ]            |             |
|  |                   |  |  [Remove Trade Button]           |             |
|  +-------------------+  +----------------------------------+             |
|                                                                          |
+--------------------------------------------------------------------------+
```

**Widgets**:
- **Left Panel**:
    - `list_strategies`: Selects active strategy.
    - `btn_new_strategy`: Opens popup dialog.
- **Right Panel** (Updates on selection):
    - `lbl_strategy_name`, `lbl_pnl`.
    - `btn_close_strategy`.
    - `tree_composition`: Columns ("Symbol", "Net Qty").
    - `btn_remove_trade`: Removes selected trade.
    - `canvas_pnl_graph`: Matplotlib figure or Tkinter drawing.
    - `btn_add_trade`: Opens popup dialog.

### Popups

#### New Strategy Dialog
- `entry_name`
- `entry_description`
- `btn_create` -> Calls `database.create_position`.

#### Add Trade Dialog
- `combo_symbol` (Populated from `options_contracts`).
- `combo_type` (BUY/SELL).
- `entry_quantity`.
- `entry_price`.
- `btn_save` -> Calls `database.add_operation`.
