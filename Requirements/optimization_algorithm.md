# Option Strategy Optimization Algorithm

This document outlines the design for an algorithm to find the optimal combination of option contracts (strategy) to maximize earnings given specific target price ranges for the underlying asset at expiration.

## 1. Problem Definition

**Objective**: Find a portfolio of option contracts (legs) $S = \{ (c_1, q_1), (c_2, q_2), \dots \}$ where $c_i$ is a contract and $q_i$ is the quantity (positive for long, negative for short) such that the profit is maximized within provided underlying price ranges.

**Inputs**:
1.  **Option Chain**: A list of available option contracts for a specific expiration.
    *   For each contract: `Strike` ($K$), `Type` (Call/Put), `Price` ($P_{market}$ or 'Last').
2.  **Target Price Ranges**: A set of disjoint intervals $[L_j, U_j]$ where the user expects the price to be at expiration.
    *   Example: `[(8211, infinity), (0, 7000)]` (Bullish breakout or Bearish breakdown).
3.  **Constraints** (Optional/Defaults):
    *   `Max Legs`: Maximum number of different contracts (e.g., 4).
    *   `Max Risk`: Maximum possible loss.
    *   `Min Liquidity`: Ignore contracts with no volume/open interest.
    *   `Budget`: Max debit allowed.

**Output**:
*   The "best" strategy combination (list of legs).
*   Performance metrics (Max Profit, Max Loss, ROI, Break-even points).

## 2. Algorithm Overview

Since the space of all possible combinations is vast, we will use a **Generative Heuristic Approach** focused on standard structures (Verticals, Calendars, Butterflies, Iron Condors) and custom multi-leg combinations constrained by "sensible" strike selection.

### Step 1: Data Filtering & Preparation
Reduce the search space coverage.
1.  **Strike Selection**: Select strikes relative to the current spot price ($S_0$) and yield target boundaries.
    *   Include strikes near $S_0$ (ATM).
    *   Include strikes near the boundaries of the Target Ranges.
2.  **Price validation**: Ensure all selected contracts have valid pricing (non-zero or bid/ask available).

### Step 2: Strategy Generation (Candidate Pool)
Generate candidate strategies from the filtered strikes.
1.  **Single Legs**: Iterate all Calls and Puts.
2.  **Vertical Spreads**: Iterate all pairs of (Long, Short) with same type.
3.  **Straddles/Strangles**: Combine Call + Put.
4.  **Butterflies/Condors**: Combine spreads.

*Optimization Note*: Instead of generating *all* permutations, generate "archetypes" and fill them with filtered strikes.

### Step 3: Evaluation
For each candidate strategy $S$:
1.  **Calculate Cost**: $Cost = \sum (q_i \cdot P_i)$.
2.  **Calculate Payoff**: Define a set of evaluation points $P_{eval}$ covering the expected range (e.g., spanning from 0.5x to 1.5x of spot price).
    *   $PnL(S_T) = \sum (q_i \cdot \text{Payoff}(c_i, S_T)) - Cost$.
3.  **Score**: Calculate a score based on the User's Objective.
    *   *Objective*: "Maximize earnings if price > X or < Y".
    *   Define **Target Zone Score**: Average (or Max) PnL in the user-defined target ranges.
        *   $Score = \frac{1}{|Points_{target}|} \sum_{S_T \in Target} PnL(S_T)$.
    *   Define **Risk Penalty**: If Max Loss exceeds threshold, discard or heavily penalize.

### Step 4: Optimization & Ranking
1.  **Sort** candidates by $Score$.
2.  **Filter** duplicates (strategies with same profile but worse pricing).
3.  **Select Top N**.

## 3. Detailed Logic Specification

```python
def find_optimal_strategy(chain, target_ranges, max_risk=None, max_legs=4):
    """
    chain: List[OptionContract]
    target_ranges: List[Tuple[float, float]] (e.g. [(8211, inf), (0, 7000)])
    """
    
    # 1. Filter Strikes
    # Identify key pivots: Current Price, Range Boundaries
    relevant_strikes = identify_relevant_strikes(chain, target_ranges)
    reduced_chain = [c for c in chain if c.strike in relevant_strikes]

    # 2. Generator
    candidates = []
    
    # A. 1-Leg (Long/Short Call/Put)
    candidates.extend(generate_single_legs(reduced_chain))
    
    # B. 2-Legs (Verticals, Straddles)
    candidates.extend(generate_verticals(reduced_chain))
    candidates.extend(generate_straddles(reduced_chain))
    
    # C. 4-Legs (Iron Condors, Butterflies) - High computation, selective generation
    candidates.extend(generate_wings(reduced_chain))

    # 3. Evaluator
    ranked_results = []
    
    # Define evaluation mesh (e.g. 100 points from min_strike*0.8 to max_strike*1.2)
    evaluation_points = create_price_mesh(chain)

    for strategy in candidates:
        # Calculate PnL Vector over mesh
        pnl_vector = calculate_pnl_profile(strategy, evaluation_points)
        
        # Calculate Metric in Target Ranges
        target_pnl = 0
        valid_points = 0
        for price, pnl in zip(evaluation_points, pnl_vector):
            if is_in_ranges(price, target_ranges):
                target_pnl += pnl
                valid_points += 1
        
        avg_target_earnings = target_pnl / max(valid_points, 1)
        
        # Check Risk Constraints
        max_loss = min(pnl_vector) # usually negative
        if max_risk and abs(max_loss) > max_risk:
            continue
            
        ranked_results.append({
            "strategy": strategy,
            "score": avg_target_earnings,
            "max_loss": max_loss,
            "max_profit": max(pnl_vector)
        })

    # 4. Sort
    ranked_results.sort(key=lambda x: x['score'], reverse=True)
    
    return ranked_results[:5]
```

## 4. Key Helper Functions to Implement

*   `identify_relevant_strikes(chain, targets)`: Intelligent selection of strikes to keep the combinatorics manageable.
*   `calculate_pnl_profile(strategy, prices)`: Vectorized calculation of payoff at expiration.
    *   Call Payoff: $Max(S_T - K, 0)$
    *   Put Payoff: $Max(K - S_T, 0)$
*   `generate_verticals(chain)`: Creates Bull/Bear Spreads.
*   `generate_wings(chain)`: Creates Iron Condors, Butterflies (Long/Short).

## 5. Future Enhancements (Linear Programming)
For strict mathematical optimization without predefined structures (e.g. "Find the absolute best 5-leg combo"):
*   Formulate as **Mixed-Integer Linear Program (MILP)**.
*   **Variables**: $x_i$ (integer quantity of contract $i$).
*   **Objective**: Max $\sum_{s \in Target} PnL(s)$.
*   **Constraints**:
    *   $\sum_{s \in All} PnL(s) \ge -Limit$ (Max Loss).
    *   $\sum |x_i| \le K$ (Max legs).
*   *Note*: This requires a solver (like Scipy MILP or OR-Tools) and may be overkill for initial version.
