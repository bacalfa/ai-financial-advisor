"""
Financial Modeling Agent.

This agent uses the "financial_modeling_valuation" Agent Skill
via Anthropic's Skills Beta API.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any

import requests
import yfinance as yf

from .base_agent import AgentResponse, AgentStatus, AgentTask, BaseAgent

logger = logging.getLogger(__name__)


class FinancialAssistantModels(BaseAgent):
    """
    Agent specialized in financial modeling and valuation using Agent Skills.

    This agent uses Anthropic's Skills Beta API to load and execute the
    "financial_modeling_valuation" skill for DCF analysis and valuation.
    """

    def __init__(
        self,
        anthropic_client: Any,
        skill_spec: dict[str, Any],
        config: dict[str, Any] = None,
    ):
        """
        Initialize the financial modeling specialist.

        Args:
            anthropic_client: Configured Anthropic API client
            skill_spec: Skill specification dict, e.g.:
                {"type": "custom", "skill_id": "financial_modeling_valuation",
                 "version": "1234567890"}
            config: Optional configuration
        """
        super().__init__(
            name="FinancialAssistantModels",
            description="Specialist in financial modeling, valuation, and forecasting",
            anthropic_client=anthropic_client,
            config=config,
        )

        self.skill_spec = skill_spec
        self.forecast_years = self.config.get("forecast_years", 5)

        logger.info(f"Initialized agent with skill: {skill_spec.get('skill_id')}")

    async def analyze(self, task: AgentTask) -> AgentResponse:
        """
        Perform financial modeling and valuation analysis.

        Args:
            task: Task with ticker and context

        Returns:
            AgentResponse with valuation assessment
        """
        try:
            logger.info(f"Building financial model for {task.ticker}")

            # Step 1: Retrieve market and financial data
            market_data = await self._retrieve_market_data(task.ticker)

            # Step 2: Build user prompt
            user_prompt = self._build_user_prompt_with_data(task, market_data)

            # Step 3: Call Claude API with Skills Beta
            response = await self._call_claude_with_skill(user_prompt)

            # Step 4: Parse response
            analysis = self._parse_response(response)

            # Step 5: Calculate confidence
            confidence = self._calculate_confidence(analysis)

            return AgentResponse(
                agent_name=self.name,
                status=AgentStatus.COMPLETED,
                confidence=confidence,
                data=analysis,
                metadata={
                    "ticker": task.ticker,
                    "forecast_years": self.forecast_years,
                    "skill_used": self.skill_spec.get("skill_id"),
                    "current_price": market_data.get("current_price", 0.0),
                },
                tokens_used=response.usage.input_tokens + response.usage.output_tokens,
            )

        except Exception as e:
            logger.error(f"Modeling failed: {str(e)}", exc_info=True)
            raise

    async def _retrieve_market_data(self, ticker: str) -> dict[str, Any]:
        """
        Retrieve current market data and comparable companies.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Market data dictionary
        """

        def get_comparable_companies(
            industry: str = None, market_cap: float = None
        ) -> list[str]:
            """
            Helper to retrieve list of comparable companies based on industry and size
            (market cap), if provided.

            Args:
                industry: Industry sector (optional)
                market_cap: Market cap (optional)

            Returns:
                List of comparable comapnies (ticker symbols)
            """
            # # FMP stock screener endpoint
            # api_key = os.environ.get("FMP_API_KEY")
            # url = f"https://financialmodelingprep.com/stable/company-screener?industry={industry}&marketCapMoreThan={market_cap}&isEtf=false&isFund=false&isActivelyTrading=true&apikey={api_key}"

            # Massive related tickers endpoint
            api_key = os.environ.get("MASSIVE_API_KEY")
            if not api_key:
                return []
            url = f"https://api.massive.com/v1/related-companies/{ticker}?apiKey={api_key}"

            try:
                response = requests.get(url)
                response.raise_for_status()  # Raise an exception for bad status codes
                companies = response.json()

                if not companies["results"]:
                    print(f"No companies found that are comparable to {ticker}")
                    return []

                return [d["ticker"] for d in companies["results"]]

            except requests.exceptions.RequestException as e:
                print(f"Error fetching data: {e}")
                return []

        # Retrieve financial data
        stock = yf.Ticker(ticker)
        fast_info = stock.fast_info
        info = stock.info

        return {
            "ticker": ticker,
            "current_price": fast_info.last_price,
            "market_cap": fast_info.market_cap,
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "peg_ratio": info.get("trailingPegRatio"),
            "price_to_book": info.get("priceToBook"),
            "price_to_sales": info.get("priceToSalesTrailing12Months"),
            "dividend_yield": info.get("dividendYield"),
            "beta": info.get("beta"),
            "comparables": get_comparable_companies(
                info.get("industry"), fast_info.market_cap
            ),
            "last_updated": datetime.now().isoformat(),
        }

    def _build_user_prompt_base(self, task: AgentTask) -> str:
        """Build base user prompt."""
        return f"""Build a comprehensive financial model and valuation for {task.company_name} ({task.ticker}).

Company: {task.company_name}
Ticker: {task.ticker}
Forecast Period: {self.forecast_years} years

User Context: {json.dumps(task.user_context, indent=2)}

Please provide a detailed valuation analysis with DCF model and comparable analysis
using your skills."""

    def _build_user_prompt_with_data(
        self, task: AgentTask, market_data: dict[str, Any]
    ) -> str:
        """Build user prompt including market data."""
        base_prompt = self._build_user_prompt_base(task)

        data_summary = f"""

Market Data Available:
Current Price: ${market_data.get("current_price", 0.0):.2f}
Market Cap: ${market_data.get("market_cap", 0.0) / 1e9:.2f}B
P/E Ratio: {market_data.get("pe_ratio", 0.0):.2f}
Forward P/E: {market_data.get("forward_pe", 0.0):.2f}
PEG Ratio: {market_data.get("peg_ratio", 0.0):.2f}
Price/Book: {market_data.get("price_to_book", 0.0):.2f}
Price/Sales: {market_data.get("price_to_sales", 0.0):.2f}
Beta: {market_data.get("beta", 1.0):.2f}

Full Market Data:
{json.dumps(market_data, indent=2, default=str)}

Based on this data, build your valuation model and provide analysis in JSON format
as specified in your skill."""

        return base_prompt + data_summary

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
        Parse Claude's response into structured valuation data.

        Args:
            response: API response from Claude

        Returns:
            Parsed valuation dictionary
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

            # analysis = FinancialAssistantModels.extract_json_from_markdown(content)
            # analysis = analysis[0]  # Expect single JSON block

            analysis = json.loads(content)

            # Validate required fields from skill
            required_fields = ["valuation", "dcf_model", "assumptions"]
            for field in required_fields:
                if field not in analysis:
                    logger.warning(f"Missing required field: {field}")
                    analysis[field] = self._get_default_value(field)

            # Add derived metrics
            if "valuation" in analysis:
                self._add_derived_metrics(analysis)

            return analysis

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            return {
                "valuation": {
                    "dcf_fair_value": 0.0,
                    "current_price": 0.0,
                    "upside_potential": 0.0,
                },
                "dcf_model": {},
                "assumptions": {},
                "strengths": [],
                "concerns": ["Unable to complete valuation"],
                "risks": ["Model uncertainty"],
                "parse_error": str(e),
            }

    def _add_derived_metrics(self, analysis: dict[str, Any]) -> None:
        """Add derived valuation metrics."""
        valuation = analysis["valuation"]

        # Calculate upside/downside if not present
        if "upside_potential" not in valuation:
            fair_value = valuation.get("dcf_fair_value", 0.0)
            current_price = valuation.get("current_price", 0.0)

            if current_price > 0:
                valuation["upside_potential"] = (
                    fair_value - current_price
                ) / current_price
            else:
                valuation["upside_potential"] = 0.0

        # Add valuation score (normalized for orchestrator)
        upside = valuation.get("upside_potential", 0.0)
        if upside >= 0.30:
            valuation["score"] = 0.9
        elif upside >= 0.15:
            valuation["score"] = 0.75
        elif upside >= 0.0:
            valuation["score"] = 0.6
        elif upside >= -0.15:
            valuation["score"] = 0.4
        else:
            valuation["score"] = 0.2

    def _get_default_value(self, field: str) -> Any:
        """Get default value for missing field."""
        defaults = {
            "valuation": {
                "dcf_fair_value": 0.0,
                "current_price": 0.0,
                "upside_potential": 0.0,
            },
            "dcf_model": {"wacc": 0.10, "terminal_growth": 0.025},
            "comparable_analysis": {},
            "assumptions": {},
            "sensitivity": {},
            "strengths": [],
            "concerns": [],
            "risks": [],
        }
        return defaults.get(field, {})

    def _calculate_confidence(self, data: dict[str, Any]) -> float:
        """
        Calculate confidence score based on model completeness.

        Args:
            data: Parsed valuation data

        Returns:
            Confidence score between 0.0 and 1.0
        """
        confidence = 1.0

        # Check for parse errors
        if "parse_error" in data:
            confidence *= 0.5

        # Check DCF model completeness
        dcf_model = data.get("dcf_model", {})
        has_wacc = "wacc" in dcf_model
        has_terminal = "terminal_growth" in dcf_model
        has_projections = len(dcf_model.get("fcf_projections", [])) > 0

        dcf_completeness = sum([has_wacc, has_terminal, has_projections]) / 3
        confidence *= 0.6 + 0.4 * dcf_completeness

        # Check valuation reasonableness
        valuation = data.get("valuation", {})
        upside = valuation.get("upside_potential", 0.0)

        # Flag extreme valuations
        if abs(upside) > 2.0:
            confidence *= 0.7
            logger.warning(f"Extreme valuation detected: {upside:.2%} upside")

        # Check WACC reasonableness (5-20%)
        wacc = dcf_model.get("wacc", 0.10)
        if not (0.05 <= wacc <= 0.20):
            confidence *= 0.8
            logger.warning(f"Unusual WACC: {wacc:.2%}")

        # Bonus for having sensitivity analysis
        if data.get("sensitivity"):
            confidence *= 1.05

        return min(1.0, max(0.0, confidence))

    def _build_system_prompt(self) -> str:
        """Not used with Skills Beta API - skill provides instructions."""
        return ""

    def _build_user_prompt(self, task: AgentTask) -> str:
        """Build user prompt for task."""
        return self._build_user_prompt_with_data(task, {})
