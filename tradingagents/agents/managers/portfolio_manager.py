"""Portfolio Manager: synthesises the risk-analyst debate into the final decision.

Uses LangChain's ``with_structured_output`` so the LLM produces a typed
``PortfolioDecision`` directly, in a single call.  The result is rendered
back to markdown for storage in ``final_trade_decision`` so memory log,
CLI display, and saved reports continue to consume the same shape they do
today.  When a provider does not expose structured output, the agent falls
back gracefully to free-text generation.
"""

from __future__ import annotations

from tradingagents.agents.schemas import PortfolioDecision, render_pm_decision
from tradingagents.agents.utils.agent_utils import (
    get_instrument_context_from_state,
    get_language_instruction,
)
from tradingagents.agents.utils.structured import (
    NO_EXTERNAL_TOOLS,
    bind_structured,
    invoke_structured_or_freetext,
)

# ── Hard R/R gate thresholds ───────────────────────────────────────────────────
# R/R below MINIMUM_RR_FOR_ENTRY → PM MUST reject Buy/Overweight and issue Hold.
# R/R below ABSOLUTE_RR_FLOOR   → PM MUST NOT approve any directional trade at all.
MINIMUM_RR_FOR_ENTRY = 1.5   # minimum acceptable R/R to enter a position
ABSOLUTE_RR_FLOOR = 1.0      # below this: no Buy or Sell under any circumstances


def create_portfolio_manager(llm):
    structured_llm = bind_structured(llm, PortfolioDecision, "Portfolio Manager")

    def portfolio_manager_node(state) -> dict:
        instrument_context = get_instrument_context_from_state(state)

        history = state["risk_debate_state"]["history"]
        risk_debate_state = state["risk_debate_state"]
        research_plan = state["investment_plan"]
        trader_plan = state["trader_investment_plan"]

        past_context = state.get("past_context", "")
        lessons_line = (
            f"- Lessons from prior decisions and outcomes:\n{past_context}\n"
            if past_context
            else ""
        )

        # ── Global single-source-of-truth market data ──────────────────────────
        # This snapshot was computed ONCE before any agent ran.
        # It is the ONLY authoritative source for current price and indicators.
        # Use ONLY these values when calculating R/R — never the ones mentioned
        # in the debate history or trader plan if they differ.
        verified_snapshot = state.get("verified_market_snapshot", "")
        snapshot_section = (
            f"\n\n---\n## AUTHORITATIVE MARKET DATA — USE ONLY THESE VALUES\n\n"
            f"{verified_snapshot}\n---\n"
            if verified_snapshot
            else ""
        )

        prompt = f"""As the Portfolio Manager, your PRIMARY DUTY is capital preservation. Synthesize the risk analysts' debate and deliver the final trading decision.

{instrument_context}
{snapshot_section}
---

**Rating Scale** (use exactly one):
- **Buy**: Strong conviction to enter or add to position (often a full position)
- **Overweight**: Favorable outlook, gradually increase exposure (e.g. tiered entry, 20-30% initial allocation)
- **Hold**: Maintain current position, wait for clearer signals
- **Underweight**: Reduce exposure, take partial profits
- **Sell**: Exit position or avoid entry completely

**Context:**
- Research Manager's investment plan: **{research_plan}**
- Trader's transaction proposal: **{trader_plan}**
{lessons_line}
**Risk Analysts Debate History:**
{history}

---

**Mandatory R/R Calculation:**
You MUST explicitly calculate and state the quantitative Risk/Reward ratio using ONLY the values in the AUTHORITATIVE MARKET DATA block above.
Formula: R/R = (Price Target − Current Price) / (Current Price − Stop Loss)
Show the exact values used and the final ratio in `risk_reward_calculation`.

---

**⛔ HARD RISK GATE — NON-NEGOTIABLE — READ CAREFULLY:**

YOU ARE THE PORTFOLIO MANAGER. YOUR SUPREME DUTY IS CAPITAL PROTECTION.

After calculating the R/R ratio:

1. **If R/R < {ABSOLUTE_RR_FLOOR} (reward is less than risk):**
   - You are ABSOLUTELY FORBIDDEN from assigning Buy, Overweight, or Sell.
   - You MUST assign **Hold** or **Underweight**.
   - You MUST explain two alternative entry scenarios with better R/R:
     * Scenario A: Entry after breakout above resistance (calculate new R/R)
     * Scenario B: Entry after pullback to support (calculate new R/R)
     * IMPORTANT: When calculating these alternative scenarios, you MUST place a realistic Stop Loss based on volatility (e.g., ATR) and spread. NEVER place a stop loss 0.01 USD away from entry, as this will result in immediate liquidation. Give the trade room to breathe.

2. **If {ABSOLUTE_RR_FLOOR} ≤ R/R < {MINIMUM_RR_FOR_ENTRY} (reward does not meet minimum threshold):**
   - You MUST NOT assign Buy or Overweight.
   - You MUST assign **Hold**, **Underweight**, or **Sell**.
   - You MUST explain the specific R/R that would justify re-entry.

3. **If the Trader's proposal is HOLD due to poor R/R:**
   - You MUST RESPECT this signal. The Trader's caution is a disciplined, correct decision.
   - You may only override it if you have CONCRETE evidence from the risk debate that
     the R/R has materially improved — and you must show the updated R/R math.

4. **If R/R ≥ {MINIMUM_RR_FOR_ENTRY}:**
   - You may assign any rating (Buy / Overweight / Hold / Underweight / Sell) based
     on the debate quality and conviction level.

Be decisive and ground every conclusion in specific evidence. Position sizing is smart
only when the R/R gate is satisfied — fractional sizing does NOT waive the R/R requirement.

{NO_EXTERNAL_TOOLS}{get_language_instruction()}"""

        final_trade_decision = invoke_structured_or_freetext(
            structured_llm,
            llm,
            prompt,
            render_pm_decision,
            "Portfolio Manager",
        )

        new_risk_debate_state = {
            "judge_decision": final_trade_decision,
            "history": risk_debate_state["history"],
            "aggressive_history": risk_debate_state["aggressive_history"],
            "conservative_history": risk_debate_state["conservative_history"],
            "neutral_history": risk_debate_state["neutral_history"],
            "latest_speaker": "Judge",
            "current_aggressive_response": risk_debate_state["current_aggressive_response"],
            "current_conservative_response": risk_debate_state["current_conservative_response"],
            "current_neutral_response": risk_debate_state["current_neutral_response"],
            "count": risk_debate_state["count"],
        }

        return {
            "risk_debate_state": new_risk_debate_state,
            "final_trade_decision": final_trade_decision,
        }

    return portfolio_manager_node

