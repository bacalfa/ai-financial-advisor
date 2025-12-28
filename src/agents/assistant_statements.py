"""
Financial Statements Analysis Agent.

This agent uses the "analyzing_financial_statements" Agent Skill
via Anthropic's Skills Beta API.
"""

import json
import logging
from datetime import datetime
from typing import Any

import yfinance as yf

from .base_agent import AgentResponse, AgentStatus, AgentTask, BaseAgent

logger = logging.getLogger(__name__)


class FinancialAssistantStatements(BaseAgent):
    """
    Agent specialized in analyzing financial statements using Agent Skills.

    This agent uses Anthropic's Skills Beta API to load and execute the
    "analyzing_financial_statements" skill for comprehensive fundamental analysis.
    """

    def __init__(
        self,
        anthropic_client: Any,
        skill_spec: dict[str, Any],
        config: dict[str, Any] = None,
    ):
        """
        Initialize the financial statements analyst.

        Args:
            anthropic_client: Configured Anthropic API client
            skill_spec: Skill specification dict, e.g.:
                {"type": "custom", "skill_id": "analyzing_financial_statements",
                 "version": "1234567890"}
            config: Optional configuration
        """
        super().__init__(
            name="FinancialAssistantStatements",
            description="Specialist in analyzing financial statements and company fundamentals",
            anthropic_client=anthropic_client,
            config=config,
        )

        self.skill_spec = skill_spec
        self.lookback_years = self.config.get("lookback_years", 3)

        logger.info(f"Initialized agent with skill: {skill_spec.get('skill_id')}")

    async def analyze(self, task: AgentTask) -> AgentResponse:
        """
        Analyze financial statements for the given company.

        Args:
            task: Task with ticker and context

        Returns:
            AgentResponse with financial health assessment
        """
        try:
            logger.info(f"Analyzing financial statements for {task.ticker}")

            # Step 1: Retrieve financial data
            financial_data = await self._retrieve_financial_data(task.ticker)

            # Step 2: Build user prompt
            user_prompt = self._build_user_prompt_with_data(task, financial_data)

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
                    "lookback_years": self.lookback_years,
                    "skill_used": self.skill_spec.get("skill_id"),
                    "data_quality": financial_data.get("quality", "unknown"),
                },
                tokens_used=response.usage.input_tokens + response.usage.output_tokens,
            )

        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}", exc_info=True)
            raise

    async def _retrieve_financial_data(self, ticker: str) -> dict[str, Any]:
        """
        Retrieve financial statements data.

        In production, this would call yfinance or SEC APIs.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Financial data dictionary
        """
        # Retrieve financial data
        stock = yf.Ticker(ticker)
        financials = stock.financials
        balance_sheet = stock.balance_sheet
        cash_flow = stock.cashflow

        # Create derived financial data
        average_cols = ["Inventory", "Accounts Receivable"]
        for c in average_cols:
            balance_sheet.loc[c + " Prev"] = balance_sheet.loc[c].shift(1)
            balance_sheet.loc["Average " + c] = 0.5 * (
                balance_sheet.loc[c] - balance_sheet.loc[c + " Prev"]
            )

        # Filter by selected financial data
        financials = financials.loc[
            [
                "EBITDA",
                "EBIT",
                "Net Income",
                "Total Revenue",
                "Cost Of Revenue",
                "Operating Income",
                "Interest Expense",
            ]
        ]
        balance_sheet = balance_sheet.loc[
            [
                "Total Assets",
                "Current Assets",
                "Current Liabilities",
                "Total Debt",
                "Stockholders Equity",
                "Inventory",
                "Cash And Cash Equivalents",
                "Average Inventory",
                "Average Accounts Receivable",
            ]
        ]
        cash_flow = cash_flow.loc[["Free Cash Flow"]]

        # Format columns
        financials.columns = financials.columns.strftime("%Y-%m-%d")
        balance_sheet.columns = balance_sheet.columns.strftime("%Y-%m-%d")
        cash_flow.columns = cash_flow.columns.strftime("%Y-%m-%d")

        return {
            "ticker": ticker,
            "income_statements": financials.to_json(),
            "balance_sheets": balance_sheet.to_json(),
            "cash_flows": cash_flow.to_json(),
            "quality": "high",
            "last_updated": datetime.now().isoformat(),
        }

    def _build_user_prompt(self, task: AgentTask) -> str:
        """Build base user prompt."""
        return f"""Analyze the financial statements for {task.company_name} ({task.ticker}).

Company: {task.company_name}
Ticker: {task.ticker}
Analysis Period: Last {self.lookback_years} years

User Context: {json.dumps(task.user_context, indent=2)}

Please provide a comprehensive financial statement analysis using your skills."""

    def _build_user_prompt_with_data(
        self, task: AgentTask, financial_data: dict[str, Any]
    ) -> str:
        """Build user prompt including financial data."""
        base_prompt = self._build_user_prompt(task)

        data_summary = f"""

Financial Data Available:
{json.dumps(financial_data, indent=2, default=str)}

Based on this data, analyze the company's financial health and provide your analysis 
in JSON format as specified in your skill."""

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
        Parse Claude's response into structured data.

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

            # Clean JSON from markdown
            content = text_content.strip()
            # if content.startswith("```json"):
            #     content = content[7:]
            # if content.startswith("```"):
            #     content = content[3:]
            # if content.endswith("```"):
            #     content = content[:-3]
            # content = content.strip()

            # analysis = json.loads(content)

            # analysis = FinancialAssistantStatements.extract_json_from_markdown(content)
            # analysis = analysis[0]  # Expect single JSON block

            analysis = json.loads(content)

            # Validate required fields from skill
            required_fields = ["health_score", "key_metrics", "strengths", "concerns"]
            for field in required_fields:
                if field not in analysis:
                    logger.warning(f"Missing required field: {field}")
                    analysis[field] = self._get_default_value(field)

            return analysis

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            return {
                "health_score": 0.5,
                "key_metrics": {},
                "strengths": [],
                "concerns": ["Unable to complete analysis"],
                "risks": ["Data quality issues"],
                "parse_error": str(e),
            }

    def _get_default_value(self, field: str) -> Any:
        """Get default value for missing field."""
        defaults = {
            "health_score": 0.5,
            "key_metrics": {},
            "strengths": [],
            "concerns": [],
            "risks": [],
            "trend_analysis": {},
        }
        return defaults.get(field, None)

    def _calculate_confidence(self, data: dict[str, Any]) -> float:
        """
        Calculate confidence score based on analysis completeness.

        Args:
            data: Parsed analysis data

        Returns:
            Confidence score between 0.0 and 1.0
        """
        confidence = 1.0

        # Check for parse errors
        if "parse_error" in data:
            confidence *= 0.5

        # Check data completeness
        key_metrics = data.get("key_metrics", {})
        metrics_count = len(key_metrics)
        expected_metrics = 11  # From skill definition
        completeness_ratio = min(metrics_count / expected_metrics, 1.0)
        confidence *= 0.5 + 0.5 * completeness_ratio

        # Check for analysis depth
        has_strengths = len(data.get("strengths", [])) > 0
        has_concerns = len(data.get("concerns", [])) > 0
        has_trends = len(data.get("trend_analysis", {})) > 0

        depth_score = sum([has_strengths, has_concerns, has_trends]) / 3
        confidence *= 0.7 + 0.3 * depth_score

        # Check health score validity
        health_score = data.get("health_score", 0.5)
        if not 0 <= health_score <= 1:
            confidence *= 0.8

        return min(1.0, max(0.0, confidence))

    def _build_system_prompt(self) -> str:
        """Not used with Skills Beta API - skill provides instructions."""
        return ""

    # def _build_user_prompt(self, task: AgentTask) -> str:
    #     """Build user prompt for task."""
    #     return self._build_user_prompt_with_data(task, {})
