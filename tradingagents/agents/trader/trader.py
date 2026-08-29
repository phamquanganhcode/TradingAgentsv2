"""Trader: turns the Research Manager's investment plan into a concrete transaction proposal."""

from __future__ import annotations

import functools

from langchain_core.messages import AIMessage

from tradingagents.agents.schemas import TraderProposal, render_trader_proposal
from tradingagents.agents.utils.agent_utils import (
    get_instrument_context_from_state,
    get_language_instruction,
)
from tradingagents.agents.utils.structured import (
    NO_EXTERNAL_TOOLS,
    bind_structured,
    invoke_structured_or_freetext,
)


def create_trader(llm):
    structured_llm = bind_structured(llm, TraderProposal, "Trader")

    def trader_node(state, name):
        company_name = state["company_of_interest"]
        instrument_context = get_instrument_context_from_state(state)
        investment_plan = state["investment_plan"]

        # ── Global single-source-of-truth market data ──────────────────────────
        # This snapshot was computed ONCE before any agent ran. Every price,
        # SMA, RSI, and ATR value you use MUST come from here. If a value in
        # the investment plan contradicts this snapshot, trust the snapshot.
        verified_snapshot = state.get("verified_market_snapshot", "")
        snapshot_section = (
            f"\n\n---\n## AUTHORITATIVE MARKET DATA (use these exact values — do not substitute)\n\n"
            f"{verified_snapshot}\n---"
            if verified_snapshot
            else ""
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a trading agent analyzing market data to make investment decisions. "
                    "Based on your analysis, provide a specific recommendation to buy, sell, or hold. "
                    "Anchor your reasoning in the analysts' reports and the research plan. "
                    "\n\n"
                    "PRICE DATA INTEGRITY RULE: The AUTHORITATIVE MARKET DATA block in the user message "
                    "is the single source of truth for current price, SMA-50, SMA-200, and all indicator values. "
                    "Use ONLY those exact numbers in your calculations. If the research plan mentions a different "
                    "current price, flag the discrepancy and use the authoritative snapshot value.\n\n"
                    "You MUST explicitly calculate and state the quantitative Risk/Reward ratio (e.g., 1:2 or 1:0.5). Do not just say 'unfavorable' without providing the specific ratio and the exact numbers used in the calculation: R/R = (Price Target - Current Price) / (Current Price - Stop Loss). "
                    "CRITICAL RULE: If the current price is too close to resistance causing the R/R ratio to be < 1:2, you MUST automatically propose 2 alternative scenarios: Scenario 1 (Wait for price to break out above resistance to buy) and Scenario 2 (Wait for price to correct to support to buy). Calculate the R/R for both of these alternative scenarios. Show the math and these scenarios in `risk_reward_calculation`.\n"
                    "STOP LOSS RULE: When placing a Stop Loss, you MUST account for the asset's normal volatility (e.g., using ATR) and typical broker spread. NEVER place a stop loss ridiculously tight (e.g. 0.01 USD away from entry). For example, if ATR is 1.81, your stop loss must be at least 0.5 to 1.5 ATR away from the entry price to avoid being instantly stopped out by noise.\n"
                    "NOTE: A HOLD recommendation when R/R < 1:2 is a disciplined, correct decision — it is NOT passive. It protects capital until a better entry with ≥ 1:2 R/R is available.\n"
                    + NO_EXTERNAL_TOOLS
                    + get_language_instruction()
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Based on a comprehensive analysis by a team of analysts, here is an investment "
                    f"plan tailored for {company_name}. {instrument_context} This plan incorporates "
                    f"insights from current technical market trends, macroeconomic indicators, and "
                    f"social media sentiment. Use this plan as a foundation for evaluating your next "
                    f"trading decision.\n\nProposed Investment Plan: {investment_plan}\n\n"
                    f"Leverage these insights to make an informed and strategic decision."
                    f"{snapshot_section}"
                ),
            },
        ]

        trader_plan = invoke_structured_or_freetext(
            structured_llm,
            llm,
            messages,
            render_trader_proposal,
            "Trader",
        )

        return {
            "messages": [AIMessage(content=trader_plan)],
            "trader_investment_plan": trader_plan,
            "sender": name,
        }

    return functools.partial(trader_node, name="Trader")

