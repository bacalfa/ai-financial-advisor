import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from src.agents.assistant_models import FinancialAssistantModels
from src.agents.assistant_statements import FinancialAssistantStatements
from src.agents.assistant_technical import FinancialAssistantTA
from src.agents.base_agent import AgentTask
from src.agents.orchestrator import FinancialAdvisor
from src.utils.skills_manager import (
    SkillsManager,
    get_agent_skill_specs_for_system,
)


async def main():
    """Main function to test the FinancialAdvisor agent."""

    load_dotenv(Path.cwd() / ".env")
    client = SkillsManager.create_client_with_skills_beta(
        api_key=os.getenv("ANTHROPIC_API_KEY")
    )
    skills_base_path = Path.cwd() / "src" / "skills"
    skill_specs = get_agent_skill_specs_for_system(client, skills_base_path)
    agent_statements = FinancialAssistantStatements(client, skill_specs["statements"])
    agent_models = FinancialAssistantModels(client, skill_specs["models"])
    agent_ta = FinancialAssistantTA(client, skill_specs["technical"])
    assistant_agents = {
        "statements": agent_statements,
        "models": agent_models,
        "technical": agent_ta,
    }
    config = {"parallel_execution": False}
    agent = FinancialAdvisor(client, assistant_agents, config=config)
    response = await agent.analyze(
        AgentTask(
            task_id="technical-analysis",
            ticker="AAPL",
            company_name="Apple Inc.",
            user_context={"risk_tolerance": "moderate"},
        )
    )
    print(response)


if __name__ == "__main__":
    asyncio.run(main())
