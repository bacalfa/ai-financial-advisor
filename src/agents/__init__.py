"""
Agents module for the financial advisory agentic AI system.

This module provides all agent implementations using Anthropic's Agent Skills Beta API.
Each agent loads and executes a specific skill via client.beta.messages.create().
"""

from .assistant_models import FinancialAssistantModels
from .assistant_statements import FinancialAssistantStatements
from .assistant_technical import FinancialAssistantTA
from .base_agent import AgentResponse, AgentStatus, AgentTask, BaseAgent
from .orchestrator import FinancialAdvisor, InvestmentRecommendation, RecommendationType

__all__ = [
    # Base classes
    "BaseAgent",
    "AgentTask",
    "AgentResponse",
    "AgentStatus",
    # Orchestrator
    "FinancialAdvisor",
    "InvestmentRecommendation",
    "RecommendationType",
    # Assistant agents
    "FinancialAssistantStatements",
    "FinancialAssistantModels",
    "FinancialAssistantTA",
]


def create_financial_advisor_system(
    anthropic_client, skill_specs: dict, config: dict = None
) -> FinancialAdvisor:
    """
    Factory function to create a complete financial advisor system using Agent Skills Beta API.

    This convenience function creates and wires together all the necessary
    agents for the financial advisory system, each with their respective Agent Skill
    specifications for use with client.beta.messages.create().

    Args:
        anthropic_client: Configured Anthropic API client with beta headers
        skill_specs: Dictionary mapping agent names to skill specifications, e.g.:
            {
                "statements": {"type": "custom", "skill_id": "analyzing-financial-statements", "version": "1234567890"},
                "models": {"type": "custom", "skill_id": "financial-modeling-valuation", "version": "1234567890"},
                "technical": {"type": "custom", "skill_id": "technical-analysis", "version": "1234567890"}
            }
        config: Optional configuration dictionary

    Returns:
        FinancialAdvisor orchestrator with all assistant agents configured

    Example:
        >>> from anthropic import Anthropic
        >>> from agents import create_financial_advisor_system
        >>> # Initialize client with Skills Beta
        >>> client = Anthropic(
        ...     api_key="your-api-key",
        ...     default_headers={"anthropic-beta": "skills-2025-10-02"},
        ... )
        >>> # Define skill specifications (versions from create_skill API calls)
        >>> skill_specs = {
        ...     "statements": {
        ...         "type": "custom",
        ...         "skill_id": "analyzing-financial-statements",
        ...         "version": "1234567890",
        ...     },
        ...     "models": {
        ...         "type": "custom",
        ...         "skill_id": "financial-modeling-valuation",
        ...         "version": "1234567890",
        ...     },
        ...     "technical": {
        ...         "type": "custom",
        ...         "skill_id": "technical-analysis",
        ...         "version": "1234567890",
        ...     },
        ... }
        >>> advisor = create_financial_advisor_system(client, skill_specs)
        >>> # Use the advisor
        >>> task = AgentTask(
        ...     task_id="analysis_001",
        ...     ticker="AAPL",
        ...     company_name="Apple Inc.",
        ...     user_context={"risk_tolerance": "moderate"},
        ... )
        >>> result = await advisor.execute(task)
        >>> print(result.data)
    """
    config = config or {}

    # Create assistant agents with their respective skill specifications
    assistant_statements = FinancialAssistantStatements(
        anthropic_client=anthropic_client,
        skill_spec=skill_specs.get("statements"),
        config=config.get("statements", {}),
    )

    assistant_models = FinancialAssistantModels(
        anthropic_client=anthropic_client,
        skill_spec=skill_specs.get("models"),
        config=config.get("models", {}),
    )

    assistant_technical = FinancialAssistantTA(
        anthropic_client=anthropic_client,
        skill_spec=skill_specs.get("technical"),
        config=config.get("technical", {}),
    )

    # Assemble assistant agents dictionary
    assistants = {
        "statements": assistant_statements,
        "models": assistant_models,
        "technical": assistant_technical,
    }

    # Create orchestrator
    orchestrator = FinancialAdvisor(
        anthropic_client=anthropic_client,
        assistant_agents=assistants,
        config=config.get("orchestrator", {}),
    )

    return orchestrator
