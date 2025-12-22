import asyncio

from src.agents.assistant_statements import FinancialAssistantStatements
from src.agents.base_agent import AgentTask


async def main():
    """Main function to test the FinancialAssistantStatements agent."""
    import os
    from pathlib import Path

    from dotenv import load_dotenv

    from src.utils.skills_manager import (
        SkillsManager,
        get_agent_skill_specs_for_system,
    )

    load_dotenv(Path.cwd() / ".env")
    client = SkillsManager.create_client_with_skills_beta(
        api_key=os.getenv("ANTHROPIC_API_KEY")
    )
    skills_base_path = Path.cwd() / "src" / "skills"
    skill_specs = get_agent_skill_specs_for_system(client, skills_base_path)
    agent = FinancialAssistantStatements(client, skill_specs["statements"])
    response = await agent.analyze(
        AgentTask(
            task_id="analyzing-financial-statements",
            ticker="AAPL",
            company_name="Apple Inc.",
            user_context={"risk_tolerance": "moderate"},
        )
    )
    print(response)


if __name__ == "__main__":
    asyncio.run(main())
