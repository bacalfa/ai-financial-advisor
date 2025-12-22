"""
Skills Manager for Anthropic's Skills Beta API.

This module provides utilities for creating, managing, and using Agent Skills
via Anthropic's Skills Beta API with client.beta.messages.create().
"""

import logging
import re
from pathlib import Path
from typing import Any

import anthropic
from anthropic.lib import files_from_dir

logger = logging.getLogger(__name__)


class SkillsManager:
    """
    Manager for Agent Skills using Anthropic's Skills Beta API.

    This class handles creating skills, managing versions, and providing
    skill specifications for use with client.beta.messages.create().
    """

    def __init__(self, anthropic_client: anthropic.Anthropic):
        """
        Initialize the Skills Manager.

        Args:
            anthropic_client: Anthropic client with Skills Beta enabled
        """
        self.client = anthropic_client

        logger.info("Initialized SkillsManager")

    def create_skill(
        self, skill_id: str, skill_directory: str, description: str | None = None
    ) -> dict[str, Any]:
        """
        Create a skill using the Skills Beta API.

        Args:
            skill_id: Unique identifier for the skill
            skill_directory: Path to directory containing SKILL.md and optional .py files
            description: Optional description (read from SKILL.md if not provided)

        Returns:
            Skill specification dict with version timestamp

        Example:
            >>> manager = SkillsManager(client)
            >>> spec = manager.create_skill(
            ...     skill_id="technical_analysis",
            ...     skill_directory="skills/technical-analysis",
            ... )
            >>> # spec = {
                "success": True,
                "skill_id": skill.id,
                "display_title": skill.display_title,
                "latest_version": skill.latest_version,
                "created_at": skill.created_at,
                "source": skill.source,
            }
        """
        skill_path = Path(skill_directory)

        if not skill_path.exists():
            raise FileNotFoundError(f"Skill directory not found: {skill_directory}")

        skill_md_path = skill_path / "SKILL.md"
        if not skill_md_path.exists():
            raise FileNotFoundError(f"SKILL.md not found in {skill_directory}")

        logger.info(f"Creating skill: {skill_id} from {skill_directory}")

        # Read SKILL.md content
        with open(skill_md_path, encoding="utf-8") as f:
            skill_content = f.read()

        # Extract description from frontmatter if not provided
        if description is None:
            description = self._extract_description_from_skill(skill_content)

        # Check for optional Python files
        python_files = list(skill_path.glob("*.py"))

        try:
            display_title = " ".join(skill_id.split("_")).title()

            # List skills and delete existing skill, if applicable
            skills_list = self.list_skills()
            for custom_skill in skills_list:
                if display_title == custom_skill["display_title"]:
                    self.delete_skill(custom_skill["skill_id"])
                    break

            # Create skill using files_from_dir
            skill = self.client.beta.skills.create(
                display_title=display_title,
                files=files_from_dir(skill_path),
            )

            logger.info(
                f"Created skill '{skill_id}' version {skill.latest_version} "
                f"({len(python_files)} Python files)"
            )

            return {
                "success": True,
                "skill_id": skill.id,
                "display_title": skill.display_title,
                "latest_version": skill.latest_version,
                "created_at": skill.created_at,
                "source": skill.source,
            }
        except Exception as e:
            logger.error(f"Create skill failed: {str(e)}", exc_info=True)
            raise

    def list_skills(self) -> list[dict[str, Any]]:
        """
        List all registered skills.

        Returns:
            Dictionary of skill_id -> skill info
        """
        try:
            skills_response = self.client.beta.skills.list(source="custom")

            skills = []
            for skill in skills_response.data:
                skills.append(
                    {
                        "skill_id": skill.id,
                        "display_title": skill.display_title,
                        "latest_version": skill.latest_version,
                        "created_at": skill.created_at,
                        "updated_at": skill.updated_at,
                    }
                )

            return skills
        except Exception as e:
            print(f"Error listing skills: {e}")
            return []

    def delete_skill(self, skill_id: str) -> bool:
        """
        Delete a custom skill and all its versions.

        Args:
            skill_id: ID of skill to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            # First delete all versions
            versions = self.client.beta.skills.versions.list(skill_id=skill_id)

            for version in versions.data:
                self.client.beta.skills.versions.delete(
                    skill_id=skill_id, version=version.version
                )

            # Then delete the skill itself
            self.client.beta.skills.delete(skill_id)
            return True

        except Exception as e:
            print(f"Error deleting skill: {e}")
            return False

    def _extract_description_from_skill(self, skill_content: str) -> str:
        """
        Extract description from SKILL.md frontmatter.

        Args:
            skill_content: Content of SKILL.md file

        Returns:
            Description string
        """
        # Try to extract from YAML frontmatter
        frontmatter_pattern = r"^---\s*\n(.*?)\n---"
        match = re.search(frontmatter_pattern, skill_content, re.DOTALL)

        if match:
            yaml_content = match.group(1)
            desc_pattern = r"description:\s*(.+?)(?:\n|$)"
            desc_match = re.search(desc_pattern, yaml_content)
            if desc_match:
                return desc_match.group(1).strip()

        return "Agent skill"

    @staticmethod
    def create_client_with_skills_beta(api_key: str) -> anthropic.Anthropic:
        """
        Create an Anthropic client with Skills Beta enabled.

        Args:
            api_key: Anthropic API key

        Returns:
            Configured Anthropic client
        """
        return anthropic.Anthropic(
            api_key=api_key, default_headers={"anthropic-beta": "skills-2025-10-02"}
        )


def setup_skills_from_directory(
    client: anthropic.Anthropic,
    skills_base_path: str,
    skill_definitions: dict[str, str],
) -> dict[str, dict[str, Any]]:
    """
    Setup multiple skills from a base directory.

    Args:
        client: Anthropic client with Skills Beta enabled
        skills_base_path: Base path containing skill directories
        skill_definitions: Dict mapping skill_id to subdirectory name, e.g.:
            {
                "analyzing-financial-statements": "financial_statements",
                "financial-modeling-valuation": "financial_models",
                "technical-analysis": "technical_analysis"
            }

    Returns:
        Dictionary mapping skill_id to skill specification

    Example:
        >>> client = SkillsManager.create_client_with_skills_beta(api_key)
        >>> skill_specs = setup_skills_from_directory(
        ...     client,
        ...     "src/skills",
        ...     {
        ...         "financial_statements": "analyzing-financial-statements",
        ...         "financial_models": "financial-modeling-valuation",
        ...         "technical_analysis": "technical-analysis",
        ...     },
        ... )
        >>> # skill_specs = {
        >>> #     "financial_statements": {"type": "custom", ...},
        >>> #     "financial_models": {"type": "custom", ...},
        >>> #     "technical_analysis": {"type": "custom", ...}
        >>> # }
    """
    manager = SkillsManager(client)
    skill_specs = {}

    base_path = Path(skills_base_path)

    for skill_id, subdirectory in skill_definitions.items():
        skill_directory = base_path / subdirectory

        try:
            spec = manager.create_skill(skill_id, str(skill_directory))
            skill_specs[skill_id] = {
                "type": "custom",
                "skill_id": spec["skill_id"],
                "version": spec["latest_version"],
            }
            logger.info(f"Successfully setup skill: {skill_id}")
        except Exception as e:
            logger.error(f"Failed to setup skill {skill_id}: {str(e)}")
            # raise

    return skill_specs


def get_agent_skill_specs_for_system(
    client: anthropic.Anthropic, skills_base_path: str = "src/skills"
) -> dict[str, dict[str, Any]]:
    """
    Convenience function to get all skill specifications for the financial advisory system.

    Args:
        client: Anthropic client with Skills Beta enabled
        skills_base_path: Base path to skills directory

    Returns:
        Dictionary with keys "statements", "models", "technical" mapping to skill specs

    Example:
        >>> from anthropic import Anthropic
        >>> from utils.skills_manager import (
        ...     SkillsManager,
        ...     get_agent_skill_specs_for_system,
        ... )
        >>> client = SkillsManager.create_client_with_skills_beta(api_key="your-key")
        >>> skill_specs = get_agent_skill_specs_for_system(client)
        >>> # Use with create_financial_advisor_system
        >>> from agents import create_financial_advisor_system
        >>> advisor = create_financial_advisor_system(client, skill_specs)
    """
    skill_definitions = {
        "financial_statements": "analyzing-financial-statements",
        "financial_models": "financial-modeling-valuation",
        "technical_analysis": "technical-analysis",
    }

    raw_specs = setup_skills_from_directory(client, skills_base_path, skill_definitions)

    # Map to agent names for convenience
    return {
        "statements": raw_specs.get("financial_statements"),
        "models": raw_specs.get("financial_models"),
        "technical": raw_specs.get("technical_analysis"),
    }
