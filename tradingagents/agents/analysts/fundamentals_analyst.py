from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tradingagents.agents.utils.agent_utils import (
    get_balance_sheet,
    get_cashflow,
    get_fundamentals,
    get_income_statement,
    get_macro_indicators,
    get_instrument_context_from_state,
    get_language_instruction,
)


def create_fundamentals_analyst(llm):
    def fundamentals_analyst_node(state):
        current_date = state["trade_date"]
        instrument_context = get_instrument_context_from_state(state)

        # ── Global single-source-of-truth price & indicator data ──────────────
        # This snapshot was computed ONCE at pipeline start and shared across
        # all agents.  The fundamentals analyst does NOT have technical-indicator
        # tools, so it MUST NOT invent price, SMA, RSI, or MA values.  Any
        # technical reference must be copied verbatim from this snapshot.
        verified_snapshot = state.get("verified_market_snapshot", "")

        tools = [
            get_fundamentals,
            get_balance_sheet,
            get_cashflow,
            get_income_statement,
            get_macro_indicators,
        ]

        system_message = (
            "You are a researcher tasked with analyzing fundamental information over the past week about an asset. Please write a comprehensive report of the fundamental information such as financial documents, macro context, and history to gain a full view of the fundamental information to inform traders. Make sure to include as much detail as possible. Provide specific, actionable insights with supporting evidence to help traders make informed decisions."
            + " Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read."
            + " Use the available tools: `get_fundamentals` for comprehensive company analysis, `get_balance_sheet`, `get_cashflow`, and `get_income_statement` for specific financial statements."
            + " CRITICAL INSTRUCTION: If the asset is a Commodity (e.g. Silver, Gold, Oil) or Forex, it does NOT have financial statements. YOU MUST CALL `get_macro_indicators` to fetch macroeconomic data like `real_yield_10y`, `dxy`, and general market conditions. You are forbidden from omitting exact numbers from `get_macro_indicators`."
            + "\n\n"
            + "MANDATORY DATA INTEGRITY RULE — TECHNICAL INDICATORS:\n"
            + "You do NOT have access to technical indicator tools (no `get_indicators`, no `get_stock_data`, no `get_verified_market_snapshot`). "
            + "You are STRICTLY FORBIDDEN from generating or reporting any values for: current price, SMA-50, SMA-200, EMA, RSI, MACD, Bollinger Bands, ATR, or any other technical indicator. "
            + "If you need to reference any such value, you MUST copy it verbatim from the VERIFIED MARKET DATA SNAPSHOT below — do NOT paraphrase or recalculate. "
            + "Reporting a number that is not in the snapshot is a critical error.\n\n"
            + "VERIFIED MARKET DATA SNAPSHOT (authoritative — do not contradict):\n"
            + (verified_snapshot if verified_snapshot else "[Snapshot unavailable — do not report any price or indicator values]")
            + get_language_instruction()
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant, collaborating with other assistants."
                    " Use the provided tools to progress towards answering the question."
                    " If you are unable to fully answer, that's OK; another assistant with different tools"
                    " will help where you left off. Execute what you can to make progress."
                    " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                    " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                    " You have access to the following tools: {tool_names}."
                    " Today's date is {current_date}; treat it as 'now' for all analysis and tool-call date ranges. {instrument_context}\n"
                    "{system_message}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(instrument_context=instrument_context)

        chain = prompt | llm.bind_tools(tools)

        result = chain.invoke(state["messages"])

        report = ""

        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            "fundamentals_report": report,
        }

    return fundamentals_analyst_node

