"""
Abstract base class for all agents in the financial advisory system.

This module provides the foundation for creating specialized financial analysis agents
that leverage Anthropic's Agent Skills framework.
"""

import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Status of agent execution"""

    IDLE = "idle"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"


@dataclass
class AgentResponse:
    """Standardized response format for all agents"""

    agent_name: str
    status: AgentStatus
    confidence: float  # 0.0 to 1.0
    data: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    execution_time: float = 0.0  # seconds
    tokens_used: int = 0

    def is_successful(self) -> bool:
        """Check if agent execution was successful"""
        return self.status == AgentStatus.COMPLETED and self.confidence >= 0.5

    def has_high_confidence(self, threshold: float = 0.8) -> bool:
        """Check if confidence meets threshold"""
        return self.confidence >= threshold


@dataclass
class AgentTask:
    """Task specification for agent execution"""

    task_id: str
    ticker: str
    company_name: str
    user_context: dict[str, Any]
    priority: int = 1  # Higher = more important
    timeout: float = 600.0  # seconds
    retry_count: int = 0
    max_retries: int = 2


class BaseAgent(ABC):
    """
    Abstract base class for all financial analysis agents.

    This class provides common functionality for agent execution, error handling,
    and integration with Anthropic's API and Agent Skills.
    """

    def __init__(
        self,
        name: str,
        description: str,
        anthropic_client: Any,
        config: dict[str, Any] | None = None,
    ):
        """
        Initialize the base agent.

        Args:
            name: Unique identifier for the agent
            description: Human-readable description of agent capabilities
            anthropic_client: Configured Anthropic API client
            config: Optional configuration parameters
        """
        self.name = name
        self.description = description
        self.client = anthropic_client
        self.config = config or {}
        self.status = AgentStatus.IDLE

        # Configuration defaults
        self.model = self.config.get("model", "claude-sonnet-4-20250514")
        self.max_tokens = self.config.get("max_tokens", 8192)
        self.temperature = self.config.get("temperature", 0.1)
        self.min_confidence = self.config.get("min_confidence", 0.7)

        logger.info(f"Initialized agent: {self.name}")

    @abstractmethod
    async def analyze(self, task: AgentTask) -> AgentResponse:
        """
        Perform analysis based on the task specification.

        This method must be implemented by all subclasses to define
        their specific analysis logic.

        Args:
            task: Task specification containing ticker, context, etc.

        Returns:
            AgentResponse with analysis results
        """
        pass

    @abstractmethod
    def _build_system_prompt(self) -> str:
        """
        Build the system prompt for the agent.

        Returns:
            System prompt string defining agent role and capabilities
        """
        pass

    @abstractmethod
    def _build_user_prompt(self, task: AgentTask) -> str:
        """
        Build the user prompt for a specific task.

        Args:
            task: Task specification

        Returns:
            User prompt string with task details
        """
        pass

    @abstractmethod
    def _parse_response(self, response: Any) -> dict[str, Any]:
        """
        Parse the Claude API response into structured data.

        Args:
            response: Raw response from Claude API

        Returns:
            Parsed data dictionary
        """
        pass

    @abstractmethod
    def _calculate_confidence(self, data: dict[str, Any]) -> float:
        """
        Calculate confidence score for the analysis.

        Args:
            data: Parsed analysis data

        Returns:
            Confidence score between 0.0 and 1.0
        """
        pass

    async def execute(self, task: AgentTask) -> AgentResponse:
        """
        Execute the agent with error handling and retry logic.

        Args:
            task: Task specification

        Returns:
            AgentResponse with results or error information
        """
        start_time = datetime.now()
        self.status = AgentStatus.PROCESSING

        try:
            logger.info(f"{self.name} starting analysis for {task.ticker}")

            # Validate task
            self._validate_task(task)

            # Execute analysis
            response = await self.analyze(task)

            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            response.execution_time = execution_time

            # Validate response
            if not response.is_successful():
                if task.retry_count < task.max_retries:
                    logger.warning(
                        f"{self.name} low confidence ({response.confidence}), "
                        f"retry {task.retry_count + 1}/{task.max_retries}"
                    )
                    task.retry_count += 1
                    return await self.execute(task)
                else:
                    logger.error(f"{self.name} failed after {task.max_retries} retries")
                    response.status = AgentStatus.FAILED

            self.status = AgentStatus.COMPLETED
            logger.info(
                f"{self.name} completed in {execution_time:.2f}s "
                f"(confidence: {response.confidence:.2f})"
            )

            return response

        except TimeoutError as e:
            logger.error(f"{self.name} timeout: {str(e)}")
            return self._create_error_response(
                task, AgentStatus.FAILED, f"Timeout after {task.timeout}s"
            )

        except Exception as e:
            logger.error(f"{self.name} error: {str(e)}", exc_info=True)

            # Retry on recoverable errors
            if task.retry_count < task.max_retries and self._is_recoverable_error(e):
                logger.info(f"{self.name} retrying after error")
                task.retry_count += 1
                return await self.execute(task)

            return self._create_error_response(task, AgentStatus.FAILED, str(e))

        finally:
            if self.status == AgentStatus.PROCESSING:
                self.status = AgentStatus.IDLE

    def _validate_task(self, task: AgentTask) -> None:
        """
        Validate task specification.

        Args:
            task: Task to validate

        Raises:
            ValueError: If task is invalid
        """
        if not task.ticker:
            raise ValueError("Ticker symbol is required")

        if not task.company_name:
            raise ValueError("Company name is required")

        if task.timeout <= 0:
            raise ValueError("Timeout must be positive")

    def _is_recoverable_error(self, error: Exception) -> bool:
        """
        Determine if an error is recoverable and should be retried.

        Args:
            error: Exception that occurred

        Returns:
            True if error is recoverable
        """
        # Network errors, rate limits, temporary API issues
        recoverable_types = (
            ConnectionError,
            TimeoutError,
        )

        if isinstance(error, recoverable_types):
            return True

        # Check for specific error messages
        error_msg = str(error).lower()
        recoverable_messages = [
            "rate limit",
            "timeout",
            "connection",
            "temporary",
            "unavailable",
        ]

        return any(msg in error_msg for msg in recoverable_messages)

    def _create_error_response(
        self, task: AgentTask, status: AgentStatus, error_message: str
    ) -> AgentResponse:
        """
        Create an error response.

        Args:
            task: Task that failed
            status: Agent status
            error_message: Error description

        Returns:
            AgentResponse indicating failure
        """
        return AgentResponse(
            agent_name=self.name,
            status=status,
            confidence=0.0,
            data={},
            errors=[error_message],
            metadata={"ticker": task.ticker, "retry_count": task.retry_count},
        )

    async def _call_claude_api(
        self, system_prompt: str, user_prompt: str, tools: list[dict] | None = None
    ) -> Any:
        """
        Make a call to Claude API with standard error handling.

        Args:
            system_prompt: System prompt defining agent role
            user_prompt: User prompt with task details
            tools: Optional tool definitions for Agent Skills

        Returns:
            API response
        """
        try:
            messages = [{"role": "user", "content": user_prompt}]

            api_params = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "system": system_prompt,
                "messages": messages,
            }

            if tools:
                api_params["tools"] = tools

            response = await self.client.messages.create(**api_params)

            return response

        except Exception as e:
            logger.error(f"Claude API call failed: {str(e)}")
            raise

    def get_status(self) -> dict[str, Any]:
        """
        Get current agent status.

        Returns:
            Dictionary with agent status information
        """
        return {
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "model": self.model,
            "config": self.config,
        }

    @staticmethod
    def extract_json_from_markdown(text):
        """
        Extracts all JSON content from a string enclosed in ```json ... ``` blocks.

        Args:
            text (str): The input string containing markdown and JSON blocks.

        Returns:
            list: A list of Python objects (dicts/lists) parsed from the JSON strings.
        """
        # Regex to find all content non-greedily between ```json and ```
        # re.DOTALL allows the '.' to match newline characters
        pattern = re.compile(r"```json(.*?)```", re.DOTALL)

        # Find all matches in the text
        matches = pattern.findall(text)

        extracted_data = []
        for match in matches:
            try:
                # Strip whitespace and parse the extracted string as JSON
                data = json.loads(match.strip())
                extracted_data.append(data)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON: {e}")
                continue

        return extracted_data
