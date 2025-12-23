"""
Technical Analysis Agent (NEW).

This agent uses the "technical_analysis" Agent Skill via Anthropic's Skills Beta API
to perform comprehensive technical analysis using pandas_ta_classic library.

This is the novel Agent Skill contribution for this project.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any

import pandas as pd
import pandas_ta_classic as ta
import yfinance as yf

from .base_agent import AgentResponse, AgentStatus, AgentTask, BaseAgent

logger = logging.getLogger(__name__)


class FinancialAssistantTA(BaseAgent):
    """
    Agent specialized in technical analysis using Agent Skills.

    This agent uses Anthropic's Skills Beta API to load and execute the
    "technical_analysis" skill with pandas_ta_classic for indicator calculations.

    This is a novel Agent Skill created specifically for this project.
    """

    def __init__(
        self,
        anthropic_client: Any,
        skill_spec: dict[str, Any],
        config: dict[str, Any] = None,
    ):
        """
        Initialize the technical analysis specialist.

        Args:
            anthropic_client: Configured Anthropic API client
            skill_spec: Skill specification dict, e.g.:
                {"type": "custom", "skill_id": "technical_analysis",
                 "version": "1234567890"}
            config: Optional configuration
        """
        super().__init__(
            name="FinancialAssistantTA",
            description="Specialist in technical analysis, chart patterns, and trading signals",
            anthropic_client=anthropic_client,
            config=config,
        )

        self.skill_spec = skill_spec
        self.lookback_days = self.config.get("lookback_days", 180)
        self.rsi_period = self.config.get("rsi_period", 14)
        self._sma_long: int = min(200, self.lookback_days)
        self.sma_periods = self.config.get("sma_periods", [20, 50, self._sma_long])

        logger.info(f"Initialized agent with skill: {skill_spec.get('skill_id')}")

    async def analyze(self, task: AgentTask) -> AgentResponse:
        """
        Perform technical analysis for the given company.

        Args:
            task: Task with ticker and context

        Returns:
            AgentResponse with technical analysis and trading signals
        """
        try:
            logger.info(f"Performing technical analysis for {task.ticker}")

            # Step 1: Retrieve price and volume data
            price_data = await self._retrieve_price_data(task.ticker)

            # Step 2: Calculate technical indicators
            indicators = await self._calculate_indicators(price_data)

            # Step 3: Build user prompt with indicator data
            user_prompt = self._build_user_prompt_with_data(task, indicators)

            # Step 4: Call Claude API with Skills Beta
            response = await self._call_claude_with_skill(user_prompt)

            # Step 5: Parse response
            analysis = self._parse_response(response)

            # Step 6: Enhance with calculated indicators
            analysis["calculated_indicators"] = indicators

            # Step 7: Calculate confidence
            confidence = self._calculate_confidence(analysis)

            return AgentResponse(
                agent_name=self.name,
                status=AgentStatus.COMPLETED,
                confidence=confidence,
                data=analysis,
                metadata={
                    "ticker": task.ticker,
                    "lookback_days": self.lookback_days,
                    "skill_used": self.skill_spec.get("skill_id"),
                    "current_price": price_data.get("current_price", 0.0),
                    "indicators_calculated": list(indicators.keys()),
                },
                tokens_used=response.usage.input_tokens + response.usage.output_tokens,
            )

        except Exception as e:
            logger.error(f"Technical analysis failed: {str(e)}", exc_info=True)
            raise

    async def _retrieve_price_data(self, ticker: str) -> dict[str, Any]:
        """
        Retrieve historical price and volume data.

        In production, this would use yfinance.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Price data dictionary with OHLCV data
        """
        # Retrieve financial data
        stock = yf.Ticker(ticker)
        hist = stock.history(period=f"{self.lookback_days}d")
        fast_info = stock.fast_info

        return {
            "ticker": ticker,
            "current_price": fast_info.last_price,
            "data_points": hist.shape[0],
            "date_range": {
                "start": (
                    datetime.now() - timedelta(days=self.lookback_days)
                ).isoformat(),
                "end": datetime.now().isoformat(),
            },
            "ohlcv": hist[["Open", "High", "Low", "Close", "Volume"]],
        }

    async def _calculate_indicators(self, price_data: dict[str, Any]) -> dict[str, Any]:
        """
        Calculate technical indicators using pandas_ta_classic.

        This is where pandas_ta_classic library would be used to calculate
        all technical indicators as specified in the Agent Skill.

        Args:
            price_data: Dictionary containing OHLCV DataFrame

        Returns:
            Dictionary of calculated indicators
        """
        try:
            # Perform actual indicator calculations
            df = price_data["ohlcv"].copy()

            if df.empty or len(df) < self.lookback_days:
                logger.warning("Insufficient data for indicator calculations")
                return {}

            # Calculate all indicators
            df["SMA_20"] = ta.sma(df["Close"], length=20)
            df["SMA_50"] = ta.sma(df["Close"], length=50)
            df[f"SMA_{self._sma_long}"] = ta.sma(df["Close"], length=self._sma_long)
            df["EMA_12"] = ta.ema(df["Close"], length=12)
            df["EMA_26"] = ta.ema(df["Close"], length=26)

            # MACD
            macd = ta.macd(df["Close"], fast=12, slow=26, signal=9)
            df = df.join(macd)

            # Momentum
            df["RSI"] = ta.rsi(df["Close"], length=14)
            stoch = ta.stoch(df["High"], df["Low"], df["Close"])
            df = df.join(stoch)
            df["Williams_R"] = ta.willr(df["High"], df["Low"], df["Close"])
            df["ROC"] = ta.roc(df["Close"], length=10)

            # Volume
            df["OBV"] = ta.obv(df["Close"], df["Volume"])
            df["Volume_SMA_20"] = ta.sma(df["Volume"], length=20)

            # Volatility
            df["ATR"] = ta.atr(df["High"], df["Low"], df["Close"], length=14)
            bbands = ta.bbands(df["Close"], length=20, std=2)
            df = df.join(bbands)

            # Get current price for reference
            # current_price = df["Close"].iloc[-1]
            current_volume = df["Volume"].iloc[-1]

            # Extract ONLY the most recent values
            indicators = {
                "trend": {
                    "sma_20": float(df["SMA_20"].iloc[-1]) if "SMA_20" in df else 0.0,
                    "sma_50": float(df["SMA_50"].iloc[-1]) if "SMA_50" in df else 0.0,
                    f"sma_{self._sma_long}": float(df[f"SMA_{self._sma_long}"].iloc[-1])
                    if f"SMA_{self._sma_long}" in df
                    else 0.0,
                    "ema_12": float(df["EMA_12"].iloc[-1]) if "EMA_12" in df else 0.0,
                    "ema_26": float(df["EMA_26"].iloc[-1]) if "EMA_26" in df else 0.0,
                    "macd": float(df["MACD_12_26_9"].iloc[-1])
                    if "MACD_12_26_9" in df
                    else 0.0,
                    "macd_signal": float(df["MACDs_12_26_9"].iloc[-1])
                    if "MACDs_12_26_9" in df
                    else 0.0,
                    "macd_histogram": float(df["MACDh_12_26_9"].iloc[-1])
                    if "MACDh_12_26_9" in df
                    else 0.0,
                },
                "momentum": {
                    "rsi_14": float(df["RSI"].iloc[-1]) if "RSI" in df else 50.0,
                    "stoch_k": float(df["STOCHk_14_3_3"].iloc[-1])
                    if "STOCHk_14_3_3" in df
                    else 50.0,
                    "stoch_d": float(df["STOCHd_14_3_3"].iloc[-1])
                    if "STOCHd_14_3_3" in df
                    else 50.0,
                    "williams_r": float(df["Williams_R"].iloc[-1])
                    if "Williams_R" in df
                    else -50.0,
                    "roc": float(df["ROC"].iloc[-1]) if "ROC" in df else 0.0,
                },
                "volume": {
                    "obv": float(df["OBV"].iloc[-1]) if "OBV" in df else 0.0,
                    "obv_trend": self._determine_obv_trend(df["OBV"]),
                    "volume_sma_20": float(df["Volume_SMA_20"].iloc[-1])
                    if "Volume_SMA_20" in df
                    else 0.0,
                    "volume_ratio": float(current_volume / df["Volume_SMA_20"].iloc[-1])
                    if "Volume_SMA_20" in df and df["Volume_SMA_20"].iloc[-1] > 0
                    else 1.0,
                },
                "volatility": {
                    "atr_14": float(df["ATR"].iloc[-1]) if "ATR" in df else 0.0,
                    "bb_upper": float(df["BBU_20_2.0"].iloc[-1])
                    if "BBU_20_2.0" in df
                    else 0.0,
                    "bb_middle": float(df["BBM_20_2.0"].iloc[-1])
                    if "BBM_20_2.0" in df
                    else 0.0,
                    "bb_lower": float(df["BBL_20_2.0"].iloc[-1])
                    if "BBL_20_2.0" in df
                    else 0.0,
                    "bb_width": float(df["BBB_20_2.0"].iloc[-1])
                    if "BBB_20_2.0" in df
                    else 0.0,
                },
                "support_resistance": {
                    "support_levels": self._calculate_support_levels(df),
                    "resistance_levels": self._calculate_resistance_levels(df),
                },
            }

            return indicators

        except Exception as e:
            logger.error(f"Indicator calculation failed: {str(e)}")
            return {}

    def _determine_obv_trend(self, obv_series: pd.Series) -> str:
        """
        Determine OBV trend from recent values.

        Args:
            obv_series: On balance volume series data

        Returns:
            Trend assessment of OBV data
        """
        if len(obv_series) < 20:
            return "neutral"

        recent_obv = obv_series.iloc[-20:]
        if recent_obv.iloc[-1] > recent_obv.iloc[0] * 1.05:
            return "bullish"
        elif recent_obv.iloc[-1] < recent_obv.iloc[0] * 0.95:
            return "bearish"
        return "neutral"

    def _calculate_support_levels(self, df: pd.DataFrame) -> list[float]:
        """
        Calculate recent support levels from swing lows.

        Args:
            df: Dataframe with OHLCV data and additional indicators

        Returns:
            List of support levels
        """
        if len(df) < 20:
            return []

        # Find local minima in the last 60 days
        recent_data = df.tail(60)
        lows = recent_data["Low"].values

        support_levels = []
        for i in range(2, len(lows) - 2):
            if (
                lows[i] < lows[i - 1]
                and lows[i] < lows[i - 2]
                and lows[i] < lows[i + 1]
                and lows[i] < lows[i + 2]
            ):
                support_levels.append(float(lows[i]))

        # Return 2-3 most recent support levels
        return sorted(support_levels)[-3:] if support_levels else []

    def _calculate_resistance_levels(self, df: pd.DataFrame) -> list[float]:
        """
        Calculate recent resistance levels from swing highs.

        Args:
            df: Dataframe with OHLCV data and additional indicators

        Returns:
            List of resistance levels
        """
        if len(df) < 20:
            return []

        # Find local maxima in the last 60 days
        recent_data = df.tail(60)
        highs = recent_data["High"].values

        resistance_levels = []
        for i in range(2, len(highs) - 2):
            if (
                highs[i] > highs[i - 1]
                and highs[i] > highs[i - 2]
                and highs[i] > highs[i + 1]
                and highs[i] > highs[i + 2]
            ):
                resistance_levels.append(float(highs[i]))

        # Return 2-3 most recent resistance levels
        return sorted(resistance_levels)[-3:] if resistance_levels else []

    def _build_user_prompt_base(self, task: AgentTask) -> str:
        """Build base user prompt."""
        return f"""Perform comprehensive technical analysis for {task.company_name} ({task.ticker}).

Company: {task.company_name}
Ticker: {task.ticker}
Analysis Period: Last {self.lookback_days} days

User Context: {json.dumps(task.user_context, indent=2)}

Please provide detailed technical analysis with trading signals using your skills."""

    def _build_user_prompt_with_data(
        self, task: AgentTask, indicators: dict[str, Any]
    ) -> str:
        """Build user prompt including calculated indicators."""
        base_prompt = self._build_user_prompt_base(task)

        indicator_summary = f"""

Pre-Calculated Technical Indicators (using pandas_ta_classic):

TREND INDICATORS:
- SMA 20: {indicators.get("trend", {}).get("sma_20", "N/A")}
- SMA 50: {indicators.get("trend", {}).get("sma_50", "N/A")}
- SMA {self._sma_long}: {indicators.get("trend", {}).get("sma_" + str(self._sma_long), "N/A")}
- EMA 12: {indicators.get("trend", {}).get("ema_12", "N/A")}
- EMA 26: {indicators.get("trend", {}).get("ema_26", "N/A")}
- MACD: {indicators.get("trend", {}).get("macd", "N/A")}
- MACD Signal: {indicators.get("trend", {}).get("macd_signal", "N/A")}
- MACD Histogram: {indicators.get("trend", {}).get("macd_histogram", "N/A")}

MOMENTUM INDICATORS:
- RSI (14): {indicators.get("momentum", {}).get("rsi_14", "N/A")}
- Stochastic %K: {indicators.get("momentum", {}).get("stoch_k", "N/A")}
- Stochastic %D: {indicators.get("momentum", {}).get("stoch_d", "N/A")}
- Williams %R: {indicators.get("momentum", {}).get("williams_r", "N/A")}
- Rate of Change: {indicators.get("momentum", {}).get("roc", "N/A")}

VOLUME INDICATORS:
- OBV: {indicators.get("volume", {}).get("obv", "N/A")}
- OBV Trend: {indicators.get("volume", {}).get("obv_trend", "N/A")}
- Volume SMA 20: {indicators.get("volume", {}).get("volume_sma_20", "N/A")}
- Volume Ratio: {indicators.get("volume", {}).get("volume_ratio", "N/A")}

VOLATILITY INDICATORS:
- ATR (14): {indicators.get("volatility", {}).get("atr_14", "N/A")}
- Bollinger Upper: {indicators.get("volatility", {}).get("bb_upper", "N/A")}
- Bollinger Middle: {indicators.get("volatility", {}).get("bb_middle", "N/A")}
- Bollinger Lower: {indicators.get("volatility", {}).get("bb_lower", "N/A")}
- Bollinger Width: {indicators.get("volatility", {}).get("bb_width", "N/A")}

SUPPORT & RESISTANCE:
- Support Levels: {indicators.get("support_resistance", {}).get("support_levels", [])}
- Resistance Levels: {indicators.get("support_resistance", {}).get("resistance_levels", [])}

Full Indicator Data:
{json.dumps(indicators, indent=2, default=str)}

Based on these technical indicators calculated using pandas_ta_classic, provide your 
comprehensive analysis in JSON format as specified in your skill."""

        return base_prompt + indicator_summary

    async def _call_claude_with_skill(self, user_prompt: str) -> Any:
        """
        Call Claude API using Skills Beta.

        Args:
            user_prompt: User prompt with task and data

        Returns:
            API response
        """
        try:
            response = self.client.beta.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                container={"skills": [self.skill_spec]},
                tools=[{"type": "code_execution_20250825", "name": "code_execution"}],
                messages=[{"role": "user", "content": user_prompt}],
                betas=[
                    "code-execution-2025-08-25",
                    "files-api-2025-04-14",
                    "skills-2025-10-02",
                ],
            )

            return response

        except Exception as e:
            logger.error(f"Claude API call with skills failed: {str(e)}")
            raise

    def _parse_response(self, response: Any) -> dict[str, Any]:
        """
        Parse Claude's response into structured technical analysis.

        Args:
            response: API response from Claude

        Returns:
            Parsed analysis dictionary
        """
        try:
            # Extract text content from response
            # text_content = ""
            # for content in response.content:
            #     if content.type == "text":
            #         text_content += content.text
            text_content = response.content[-1].text

            # Clean JSON
            content = text_content.strip()
            # if content.startswith("```json"):
            #     content = content[7:]
            # if content.startswith("```"):
            #     content = content[3:]
            # if content.endswith("```"):
            #     content = content[:-3]
            # content = content.strip()

            # analysis = json.loads(content)

            analysis = FinancialAssistantTA.extract_json_from_markdown(content)
            analysis = analysis[0]  # Expect single JSON block

            # Validate required fields from skill
            required_fields = ["technical_score", "signals", "indicators"]
            for field in required_fields:
                if field not in analysis:
                    logger.warning(f"Missing required field: {field}")
                    analysis[field] = self._get_default_value(field)

            return analysis

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            return {
                "technical_score": 0.5,
                "signals": {
                    "trend": "neutral",
                    "momentum": "neutral",
                    "volume": "neutral",
                },
                "indicators": {},
                "patterns": [],
                "strengths": [],
                "concerns": ["Unable to complete technical analysis"],
                "risks": ["Analysis uncertainty"],
                "parse_error": str(e),
            }

    def _get_default_value(self, field: str) -> Any:
        """Get default value for missing field."""
        defaults = {
            "technical_score": 0.5,
            "signals": {
                "trend": "neutral",
                "momentum": "neutral",
                "volume": "neutral",
                "volatility": "medium",
            },
            "indicators": {},
            "patterns": [],
            "support_resistance": {"key_support": [], "key_resistance": []},
            "trading_setup": {"bias": "neutral", "entry_points": [], "targets": []},
            "strengths": [],
            "concerns": [],
            "risks": [],
        }
        return defaults.get(field, None)

    def _calculate_confidence(self, data: dict[str, Any]) -> float:
        """
        Calculate confidence based on indicator completeness and signal clarity.

        Args:
            data: Parsed technical analysis data

        Returns:
            Confidence score between 0.0 and 1.0
        """
        confidence = 1.0

        # Check for parse errors
        if "parse_error" in data:
            confidence *= 0.5

        # Check indicator completeness
        calculated = data.get("calculated_indicators", {})
        expected_categories = ["trend", "momentum", "volume", "volatility"]
        available_categories = sum(
            1 for cat in expected_categories if calculated.get(cat)
        )
        completeness = available_categories / len(expected_categories)
        confidence *= 0.6 + 0.4 * completeness

        # Check signal clarity
        signals = data.get("signals", {})
        neutral_count = sum(1 for signal in signals.values() if signal == "neutral")
        total_signals = len(signals) if signals else 1
        clarity = 1.0 - (neutral_count / total_signals) * 0.3
        confidence *= clarity

        # Bonus for identified patterns
        patterns = data.get("patterns", [])
        if patterns:
            confidence *= 1.1

        # Check trading setup completeness
        trading_setup = data.get("trading_setup", {})
        has_bias = trading_setup.get("bias") != "neutral"
        has_entries = len(trading_setup.get("entry_points", [])) > 0
        has_targets = len(trading_setup.get("targets", [])) > 0

        setup_completeness = sum([has_bias, has_entries, has_targets]) / 3
        confidence *= 0.8 + 0.2 * setup_completeness

        return min(1.0, max(0.0, confidence))

    def _build_system_prompt(self) -> str:
        """Not used with Skills Beta API - skill provides instructions."""
        return ""

    def _build_user_prompt(self, task: AgentTask) -> str:
        """Build user prompt for task."""
        return self._build_user_prompt_with_data(task, {})
