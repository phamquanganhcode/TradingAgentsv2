# TradingAgents/graph/propagation.py

import logging
from typing import Any

from tradingagents.agents.utils.agent_states import (
    InvestDebateState,
    RiskDebateState,
)

logger = logging.getLogger(__name__)


class Propagator:
    """Handles state initialization and propagation through the graph."""

    def __init__(self, max_recur_limit=100):
        """Initialize with configuration parameters."""
        self.max_recur_limit = max_recur_limit

    def _fetch_verified_snapshot(self, company_name: str, trade_date: str) -> str:
        """Fetch the deterministic market-data snapshot once at run start.

        This is the SINGLE authoritative source for price, SMA-50, SMA-200,
        RSI, ATR, Bollinger bands, and recent closes.  Every downstream agent
        receives this text and MUST NOT invent or recalculate numbers that
        conflict with it.  Failures are caught and a clear error message is
        returned instead — the pipeline never blocks on a data failure here.
        """
        try:
            from tradingagents.dataflows.market_data_validator import (
                build_verified_market_snapshot,
            )
            return build_verified_market_snapshot(company_name, trade_date)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Could not build verified market snapshot for %s on %s: %s",
                company_name, trade_date, exc,
            )
            return (
                f"[Verified market snapshot unavailable for {company_name} on "
                f"{trade_date}: {exc}. Agents must explicitly note this limitation "
                f"and must NOT invent price or indicator values.]"
            )

    def create_initial_state(
        self,
        company_name: str,
        trade_date: str,
        asset_type: str = "stock",
        past_context: str = "",
        instrument_context: str = "",
    ) -> dict[str, Any]:
        """Create the initial state for the agent graph.

        ``instrument_context`` is the deterministic ticker-identity string
        resolved once at run start (see
        ``TradingAgentsGraph.resolve_instrument_context``). When empty, agents
        fall back to ticker-only context via
        ``get_instrument_context_from_state``.

        ``verified_market_snapshot`` is computed here — ONCE — so every
        agent in the pipeline shares the exact same price and indicator
        values.  This prevents the data-skew bug where different agents
        report different current prices or moving-average values.
        """
        # ── Fetch global market data snapshot ──────────────────────────────────
        # This is the authoritative source of truth for all numeric market data.
        # Computed before any agent runs so every node reads the same numbers.
        verified_market_snapshot = self._fetch_verified_snapshot(
            company_name, trade_date
        )

        return {
            "messages": [("human", company_name)],
            "company_of_interest": company_name,
            "asset_type": asset_type,
            "instrument_context": instrument_context,
            "trade_date": str(trade_date),
            "past_context": past_context,
            # ── Single source of truth for all market data ──────────────────
            "verified_market_snapshot": verified_market_snapshot,
            "investment_debate_state": InvestDebateState(
                {
                    "bull_history": "",
                    "bear_history": "",
                    "history": "",
                    "current_response": "",
                    "judge_decision": "",
                    "count": 0,
                }
            ),
            "risk_debate_state": RiskDebateState(
                {
                    "aggressive_history": "",
                    "conservative_history": "",
                    "neutral_history": "",
                    "history": "",
                    "latest_speaker": "",
                    "current_aggressive_response": "",
                    "current_conservative_response": "",
                    "current_neutral_response": "",
                    "judge_decision": "",
                    "count": 0,
                }
            ),
            "market_report": "",
            "fundamentals_report": "",
            "sentiment_report": "",
            "news_report": "",
        }

    def get_graph_args(self, callbacks: list | None = None) -> dict[str, Any]:
        """Get arguments for the graph invocation.

        Args:
            callbacks: Optional list of callback handlers for tool execution tracking.
                       Note: LLM callbacks are handled separately via LLM constructor.
        """
        config = {"recursion_limit": self.max_recur_limit}
        if callbacks:
            config["callbacks"] = callbacks
        return {
            "stream_mode": "values",
            "config": config,
        }
