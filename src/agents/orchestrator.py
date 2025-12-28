"""
Orchestrator agent that coordinates financial analysis across specialized assistants.

The FinancialAdvisor acts as the main point of interaction with users, delegating
tasks to specialized assistants and synthesizing their findings into actionable
investment recommendations.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import anthropic

from .base_agent import AgentResponse, AgentStatus, AgentTask, BaseAgent

logger = logging.getLogger(__name__)


class RecommendationType:
    """Investment recommendation types"""

    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass
class InvestmentRecommendation:
    """Final investment recommendation with supporting analysis"""

    ticker: str
    company_name: str
    recommendation: str
    confidence: float
    composite_score: float

    # Component scores
    fundamental_score: float
    technical_score: float
    consistency_score: float

    # Detailed analysis from each agent
    statements_analysis: dict[str, Any]
    models_analysis: dict[str, Any]
    technical_analysis: dict[str, Any]

    # Summary insights
    key_strengths: list[str]
    key_concerns: list[str]
    risk_factors: list[str]

    # Metadata
    analysis_timestamp: datetime
    total_execution_time: float
    agents_consulted: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "recommendation": self.recommendation,
            "confidence": round(self.confidence, 3),
            "composite_score": round(self.composite_score, 3),
            "scores": {
                "fundamental": round(self.fundamental_score, 3),
                "technical": round(self.technical_score, 3),
                "consistency": round(self.consistency_score, 3),
            },
            "analysis": {
                "statements": self.statements_analysis,
                "models": self.models_analysis,
                "technical": self.technical_analysis,
            },
            "insights": {
                "strengths": self.key_strengths,
                "concerns": self.key_concerns,
                "risks": self.risk_factors,
            },
            "metadata": {
                "timestamp": self.analysis_timestamp.isoformat(),
                "execution_time": round(self.total_execution_time, 2),
                "agents": self.agents_consulted,
            },
        }


class FinancialAdvisor(BaseAgent):
    """
    Orchestrator agent that coordinates financial analysis across specialized assistants.

    This agent manages the overall workflow of investment analysis by:
    1. Parsing user queries and extracting investment requirements
    2. Delegating tasks to specialized financial assistants
    3. Judging and synthesizing results from multiple agents
    4. Managing feedback loops for incomplete or conflicting data
    5. Generating comprehensive investment recommendations
    """

    def __init__(
        self,
        anthropic_client: anthropic.Anthropic,
        assistant_agents: dict[str, BaseAgent],
        config: dict[str, Any] | None = None,
    ):
        """
        Initialize the Financial Advisor orchestrator.

        Args:
            anthropic_client: Configured Anthropic API client
            assistant_agents: Dictionary of specialized assistant agents
            config: Optional configuration parameters
        """
        super().__init__(
            name="FinancialAdvisor",
            description="Senior financial advisor coordinating comprehensive investment analysis",
            anthropic_client=anthropic_client,
            config=config,
        )

        self.assistants = assistant_agents

        # Orchestrator-specific config
        self.weights = self.config.get(
            "weights", {"fundamental": 0.50, "technical": 0.30, "consistency": 0.20}
        )

        self.thresholds = self.config.get(
            "thresholds", {"strong_buy": 0.80, "buy": 0.65, "hold": 0.45, "sell": 0.30}
        )

        self.min_agent_confidence = self.config.get("min_agent_confidence", 0.70)
        self.parallel_execution = self.config.get("parallel_execution", True)

        logger.info(
            f"Initialized orchestrator with {len(self.assistants)} assistants: "
            f"{list(self.assistants.keys())}"
        )

    async def analyze(self, task: AgentTask) -> AgentResponse:
        """
        Orchestrate comprehensive investment analysis.

        Args:
            task: Task specification with ticker and user context

        Returns:
            AgentResponse with investment recommendation
        """
        start_time = datetime.now()

        try:
            # Step 1: Delegate tasks to assistant agents
            logger.info(f"Delegating analysis tasks for {task.ticker}")
            agent_results = await self._delegate_tasks(task)

            # Step 2: Validate results
            validation_result = self._validate_agent_results(agent_results)

            if not validation_result["is_valid"]:
                # Request clarifications if needed
                if validation_result["retry_needed"]:
                    logger.warning("Some agents need retry, initiating feedback loop")
                    agent_results = await self._feedback_loop(
                        task, agent_results, validation_result["retry_agents"]
                    )
                else:
                    logger.error("Insufficient data for recommendation")
                    return self._create_insufficient_data_response(task, agent_results)

            # Step 3: Judge and synthesize results
            logger.info("Synthesizing results from all agents")
            recommendation = self._synthesize_recommendation(task, agent_results)

            # Step 4: Create response
            execution_time = (datetime.now() - start_time).total_seconds()

            return AgentResponse(
                agent_name=self.name,
                status=AgentStatus.COMPLETED,
                confidence=recommendation.confidence,
                data=recommendation.to_dict(),
                metadata={
                    "agents_consulted": recommendation.agents_consulted,
                    "parallel_execution": self.parallel_execution,
                },
                execution_time=execution_time,
                tokens_used=sum(r.tokens_used for r in agent_results.values()),
            )

        except Exception as e:
            logger.error(f"Orchestration failed: {str(e)}", exc_info=True)
            raise

    async def _delegate_tasks(self, task: AgentTask) -> dict[str, AgentResponse]:
        """
        Delegate analysis tasks to assistant agents.

        Args:
            task: Task specification

        Returns:
            Dictionary mapping agent names to their responses
        """
        if self.parallel_execution:
            # Execute all agents in parallel
            tasks_to_run = [agent.execute(task) for agent in self.assistants.values()]

            results = await asyncio.gather(*tasks_to_run, return_exceptions=True)

            # Map results back to agent names
            agent_results = {}
            for agent_name, result in zip(self.assistants.keys(), results):
                if isinstance(result, Exception):
                    logger.error(f"Agent {agent_name} failed: {str(result)}")
                    agent_results[agent_name] = self._create_error_response(
                        task, AgentStatus.FAILED, str(result)
                    )
                else:
                    agent_results[agent_name] = result

            return agent_results
        else:
            # Execute agents sequentially
            agent_results = {}
            for agent_name, agent in self.assistants.items():
                try:
                    result = await agent.execute(task)
                    agent_results[agent_name] = result
                except Exception as e:
                    logger.error(f"Agent {agent_name} failed: {str(e)}")
                    agent_results[agent_name] = self._create_error_response(
                        task, AgentStatus.FAILED, str(e)
                    )

                if self.config.get("sequential_sleep"):
                    # Set this parameter if a rate limit error occurs depending on payment tier
                    time.sleep(self.config.get("sequential_sleep"))

            return agent_results

    def _validate_agent_results(
        self, agent_results: dict[str, AgentResponse]
    ) -> dict[str, Any]:
        """
        Validate results from assistant agents.

        Args:
            agent_results: Results from all agents

        Returns:
            Validation result with retry recommendations
        """
        validation = {
            "is_valid": True,
            "retry_needed": False,
            "retry_agents": [],
            "issues": [],
        }

        # Check each agent's result
        for agent_name, response in agent_results.items():
            if response.status == AgentStatus.FAILED:
                validation["issues"].append(f"{agent_name} failed completely")
                validation["is_valid"] = False

            elif not response.is_successful():
                validation["issues"].append(
                    f"{agent_name} low confidence: {response.confidence:.2f}"
                )
                if response.confidence > 0.3:  # Partial data available
                    validation["retry_needed"] = True
                    validation["retry_agents"].append(agent_name)
                else:
                    validation["is_valid"] = False

            elif not response.has_high_confidence(self.min_agent_confidence):
                validation["issues"].append(
                    f"{agent_name} below threshold: {response.confidence:.2f}"
                )

        # Need at least 2 successful agents for a recommendation
        successful_agents = sum(1 for r in agent_results.values() if r.is_successful())

        if successful_agents < 2:
            validation["is_valid"] = False
            validation["issues"].append(
                f"Only {successful_agents} agents succeeded (need 2+)"
            )

        if validation["issues"]:
            logger.warning(f"Validation issues: {validation['issues']}")

        return validation

    async def _feedback_loop(
        self,
        task: AgentTask,
        agent_results: dict[str, AgentResponse],
        retry_agents: list[str],
    ) -> dict[str, AgentResponse]:
        """
        Implement feedback loop to improve low-confidence results.

        Args:
            task: Original task
            agent_results: Current agent results
            retry_agents: List of agents to retry

        Returns:
            Updated agent results
        """
        logger.info(f"Retrying agents: {retry_agents}")

        # Create enhanced task with context from successful agents
        enhanced_task = self._enhance_task_with_context(task, agent_results)

        # Retry specific agents
        retry_tasks = [
            self.assistants[agent_name].execute(enhanced_task)
            for agent_name in retry_agents
            if agent_name in self.assistants
        ]

        retry_results = await asyncio.gather(*retry_tasks, return_exceptions=True)

        # Update results
        for agent_name, result in zip(retry_agents, retry_results):
            if not isinstance(result, Exception):
                agent_results[agent_name] = result
                logger.info(
                    f"Retry for {agent_name} completed "
                    f"(confidence: {result.confidence:.2f})"
                )

        return agent_results

    def _enhance_task_with_context(
        self, task: AgentTask, agent_results: dict[str, AgentResponse]
    ) -> AgentTask:
        """
        Enhance task with context from successful agents.

        Args:
            task: Original task
            agent_results: Results from all agents

        Returns:
            Enhanced task with additional context
        """
        enhanced_context = task.user_context.copy()

        # Add insights from successful agents
        enhanced_context["successful_analyses"] = {
            agent_name: response.data
            for agent_name, response in agent_results.items()
            if response.is_successful()
        }

        return AgentTask(
            task_id=f"{task.task_id}_enhanced",
            ticker=task.ticker,
            company_name=task.company_name,
            user_context=enhanced_context,
            priority=task.priority,
            timeout=task.timeout,
            retry_count=task.retry_count,
            max_retries=task.max_retries,
        )

    def _synthesize_recommendation(
        self, task: AgentTask, agent_results: dict[str, AgentResponse]
    ) -> InvestmentRecommendation:
        """
        Synthesize final recommendation from agent results.

        Args:
            task: Task specification
            agent_results: Results from all agents

        Returns:
            Investment recommendation
        """
        # Extract scores from each category
        statements_score = self._extract_score(agent_results, "statements")
        models_score = self._extract_score(agent_results, "models")
        technical_score = self._extract_score(agent_results, "technical")

        # Calculate fundamental score (average of statements and models)
        fundamental_score = (statements_score + models_score) / 2

        # Calculate consistency score
        consistency_score = self._calculate_consistency(agent_results)

        # Calculate weighted composite score
        composite_score = (
            self.weights["fundamental"] * fundamental_score
            + self.weights["technical"] * technical_score
            + self.weights["consistency"] * consistency_score
        )

        # Determine recommendation
        recommendation_type = self._determine_recommendation(composite_score)

        # Calculate overall confidence
        confidence = self._calculate_overall_confidence(
            agent_results, consistency_score
        )

        # Extract insights
        strengths, concerns, risks = self._extract_insights(agent_results)

        # Get execution time
        total_time = sum(r.execution_time for r in agent_results.values())

        return InvestmentRecommendation(
            ticker=task.ticker,
            company_name=task.company_name,
            recommendation=recommendation_type,
            confidence=confidence,
            composite_score=composite_score,
            fundamental_score=fundamental_score,
            technical_score=technical_score,
            consistency_score=consistency_score,
            statements_analysis=agent_results.get(
                "statements",
                AgentResponse(
                    agent_name="statements",
                    status=AgentStatus.FAILED,
                    confidence=0.0,
                    data={},
                ),
            ).data,
            models_analysis=agent_results.get(
                "models",
                AgentResponse(
                    agent_name="models",
                    status=AgentStatus.FAILED,
                    confidence=0.0,
                    data={},
                ),
            ).data,
            technical_analysis=agent_results.get(
                "technical",
                AgentResponse(
                    agent_name="technical",
                    status=AgentStatus.FAILED,
                    confidence=0.0,
                    data={},
                ),
            ).data,
            key_strengths=strengths,
            key_concerns=concerns,
            risk_factors=risks,
            analysis_timestamp=datetime.now(),
            total_execution_time=total_time,
            agents_consulted=list(agent_results.keys()),
        )

    def _extract_score(
        self, agent_results: dict[str, AgentResponse], agent_type: str
    ) -> float:
        """Extract score from specific agent type"""
        for agent_name, response in agent_results.items():
            if agent_type in agent_name.lower() and response.is_successful():
                # Extract health_score, technical_score, or valuation score
                data = response.data
                return (
                    data.get("health_score", 0.0)
                    or data.get("technical_score", 0.0)
                    or data.get("valuation", {}).get("score", 0.0)
                    or 0.5  # Default neutral score
                )
        return 0.5  # Neutral if agent not found

    def _calculate_consistency(self, agent_results: dict[str, AgentResponse]) -> float:
        """
        Calculate consistency score between fundamental and technical analysis.

        Args:
            agent_results: Results from all agents

        Returns:
            Consistency score between 0.0 and 1.0
        """
        # Extract recommendations or signals
        fundamental_signal = None
        technical_signal = None

        for agent_name, response in agent_results.items():
            if not response.is_successful():
                continue

            if "statements" in agent_name.lower() or "models" in agent_name.lower():
                # Positive if scores are high
                score = self._extract_score(agent_results, agent_name.lower())
                fundamental_signal = "bullish" if score > 0.6 else "bearish"

            elif "technical" in agent_name.lower():
                signals = response.data.get("signals", {})
                technical_signal = signals.get("trend", "neutral")

        # Calculate alignment
        if fundamental_signal and technical_signal:
            if fundamental_signal == "bullish" and technical_signal == "bullish":
                return 1.0
            elif fundamental_signal == "bearish" and technical_signal == "bearish":
                return 1.0
            else:
                return 0.3  # Conflicting signals

        return 0.5  # Neutral if signals unavailable

    def _determine_recommendation(self, composite_score: float) -> str:
        """Determine recommendation type based on composite score"""
        if composite_score >= self.thresholds["strong_buy"]:
            return RecommendationType.STRONG_BUY
        elif composite_score >= self.thresholds["buy"]:
            return RecommendationType.BUY
        elif composite_score >= self.thresholds["hold"]:
            return RecommendationType.HOLD
        elif composite_score >= self.thresholds["sell"]:
            return RecommendationType.SELL
        else:
            return RecommendationType.STRONG_SELL

    def _calculate_overall_confidence(
        self, agent_results: dict[str, AgentResponse], consistency_score: float
    ) -> float:
        """Calculate overall confidence in the recommendation"""
        # Average confidence from successful agents
        successful_results = [r for r in agent_results.values() if r.is_successful()]

        if not successful_results:
            return 0.0

        avg_confidence = sum(r.confidence for r in successful_results) / len(
            successful_results
        )

        # Boost confidence if signals are consistent
        confidence_boost = (consistency_score - 0.5) * 0.2

        return min(1.0, avg_confidence + confidence_boost)

    def _extract_insights(
        self, agent_results: dict[str, AgentResponse]
    ) -> tuple[list[str], list[str], list[str]]:
        """Extract key insights from all agent results"""
        strengths = []
        concerns = []
        risks = []

        for response in agent_results.values():
            if not response.is_successful():
                continue

            data = response.data
            strengths.extend(data.get("strengths", []))
            concerns.extend(data.get("concerns", []))
            risks.extend(data.get("risks", []))

        # Deduplicate and limit
        return (list(set(strengths))[:5], list(set(concerns))[:5], list(set(risks))[:3])

    def _create_insufficient_data_response(
        self, task: AgentTask, agent_results: dict[str, AgentResponse]
    ) -> AgentResponse:
        """Create response for insufficient data scenario"""
        errors = []
        for agent_name, response in agent_results.items():
            if not response.is_successful():
                errors.append(f"{agent_name}: {', '.join(response.errors)}")

        return AgentResponse(
            agent_name=self.name,
            status=AgentStatus.COMPLETED,
            confidence=0.0,
            data={
                "recommendation": RecommendationType.INSUFFICIENT_DATA,
                "reason": "Unable to gather sufficient data for analysis",
                "partial_results": {
                    name: result.data
                    for name, result in agent_results.items()
                    if result.data
                },
            },
            errors=errors,
        )

    def _build_system_prompt(self) -> str:
        """Build system prompt for orchestrator"""
        return """You are a senior financial advisor with extensive experience in investment analysis.
Your role is to coordinate analysis across specialized teams and synthesize their findings
into clear, actionable investment recommendations."""

    def _build_user_prompt(self, task: AgentTask) -> str:
        """Build user prompt for orchestrator"""
        return f"""Analyze investment opportunity for {task.company_name} ({task.ticker}).
User context: {json.dumps(task.user_context, indent=2)}"""

    def _parse_response(self, response: Any) -> dict[str, Any]:
        """Parse orchestrator response"""
        return {}  # Not directly used by orchestrator

    def _calculate_confidence(self, data: dict[str, Any]) -> float:
        """Calculate orchestrator confidence"""
        return data.get("confidence", 0.0)
