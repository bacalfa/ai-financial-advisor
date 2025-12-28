"""
Complete usage example for the Financial Advisory Agentic AI System.

This script demonstrates how to:
1. Initialize the system with Agent Skills
2. Run comprehensive investment analysis
3. Generate a professional PDF report
"""

import asyncio
import logging
import os
from pathlib import Path

from src.agents import AgentStatus, AgentTask, create_financial_advisor_system
from src.agents.report_generator import ReportGenerator
from src.utils.skills_manager import SkillsManager, get_agent_skill_specs_for_system

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main(
    task_id="analysis_001",
    ticker="AAPL",
    company_name="Apple Inc.",
):
    """
    Main execution flow for investment analysis.
    """

    # ============================================================
    # Step 1: Initialize Anthropic Client with Skills Beta
    # ============================================================

    logger.info("Initializing Anthropic client with Skills Beta...")

    # Get API key from environment or configuration
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")

    # Create client with Skills Beta enabled
    client = SkillsManager.create_client_with_skills_beta(api_key)

    logger.info("✓ Client initialized")

    # ============================================================
    # Step 2: Setup Agent Skills
    # ============================================================

    logger.info("Setting up Agent Skills...")

    # Create skill specifications from skill directories
    skill_specs = get_agent_skill_specs_for_system(
        client=client, skills_base_path="src/skills"
    )

    logger.info(f"✓ Loaded {len(skill_specs)} Agent Skills:")
    for name, spec in skill_specs.items():
        logger.info(f"  - {name}: {spec['skill_id']} (v{spec['version']})")

    # ============================================================
    # Step 3: Create Financial Advisor System
    # ============================================================

    logger.info("Creating Financial Advisor system...")

    # Optional: Configure agent parameters
    config = {
        "orchestrator": {
            "weights": {"fundamental": 0.50, "technical": 0.30, "consistency": 0.20},
            "thresholds": {"strong_buy": 0.80, "buy": 0.65, "hold": 0.45, "sell": 0.30},
            "parallel_execution": False,
            "sequential_sleep": 90,
        },
        "statements": {
            "lookback_years": 3,
            "sequential_sleep": 90,
        },
        "models": {
            "forecast_years": 5,
            "sequential_sleep": 90,
        },
        "technical": {
            "lookback_days": 180,
            "rsi_period": 14,
            "sma_periods": [20, 50, 200],
            "sequential_sleep": 90,
        },
    }

    advisor = create_financial_advisor_system(
        anthropic_client=client, skill_specs=skill_specs, config=config
    )

    logger.info("✓ Financial Advisor system created")

    # ============================================================
    # Step 4: Define Investment Analysis Task
    # ============================================================

    logger.info("Defining analysis task...")

    # Example: Analyze Apple Inc. (AAPL)
    task = AgentTask(
        task_id=task_id,
        ticker=ticker,
        company_name=company_name,
        user_context={
            "risk_tolerance": "moderate",
            "investment_horizon": "long-term",
            "investment_amount": 50000,
            "notes": "Looking for growth stocks in technology sector",
            # "sector_preference": "technology",
            # "min_market_cap": 100e9,  # $100B minimum
            # "max_debt_to_equity": 0.5,
            # "min_roe": 0.15,  # 15% minimum ROE
            # "notes": "High-growth technology stocks with strong fundamentals",
        },
        priority=1,
        timeout=120.0,  # 2 minutes per agent
    )

    logger.info(f"✓ Task defined: {task.ticker} - {task.company_name}")

    # ============================================================
    # Step 5: Execute Comprehensive Analysis
    # ============================================================

    logger.info("=" * 60)
    logger.info("STARTING INVESTMENT ANALYSIS")
    logger.info("=" * 60)

    try:
        # Execute analysis (orchestrator coordinates all agents)
        result = await advisor.execute(task)

        logger.info("=" * 60)
        logger.info("ANALYSIS COMPLETED")
        logger.info("=" * 60)

        # Check if analysis was successful
        if result.status == AgentStatus.COMPLETED:
            logger.info("✓ Analysis completed successfully")

            # Extract recommendation data
            recommendation = result.data

            # Display summary
            logger.info("")
            logger.info("INVESTMENT RECOMMENDATION SUMMARY")
            logger.info("-" * 60)
            logger.info(
                f"Company: {recommendation['company_name']} ({recommendation['ticker']})"
            )
            logger.info(f"Recommendation: {recommendation['recommendation']}")
            logger.info(f"Confidence: {recommendation['confidence']:.1%}")
            logger.info(f"Composite Score: {recommendation['composite_score']:.2f}/1.0")
            logger.info("")
            logger.info("Score Breakdown:")
            logger.info(
                f"  - Fundamental: {recommendation['scores']['fundamental']:.2f}"
            )
            logger.info(f"  - Technical: {recommendation['scores']['technical']:.2f}")
            logger.info(
                f"  - Consistency: {recommendation['scores']['consistency']:.2f}"
            )
            logger.info("")
            logger.info("Key Strengths:")
            for strength in recommendation["insights"]["strengths"][:3]:
                logger.info(f"  • {strength}")
            logger.info("")
            logger.info("Key Concerns:")
            for concern in recommendation["insights"]["concerns"][:3]:
                logger.info(f"  • {concern}")
            logger.info("")
            logger.info("Execution Statistics:")
            logger.info(
                f"  - Total Time: {recommendation['metadata']['execution_time']:.2f}s"
            )
            logger.info(
                f"  - Agents Consulted: {', '.join(recommendation['analysis'])}"
            )
            logger.info("-" * 60)

        else:
            logger.error(f"✗ Analysis failed with status: {result.status}")
            if result.errors:
                for error in result.errors:
                    logger.error(f"  Error: {error}")
            return

        # ============================================================
        # Step 6: Generate PDF Report
        # ============================================================

        logger.info("")
        logger.info("=" * 60)
        logger.info("GENERATING PDF REPORT")
        logger.info("=" * 60)

        # Initialize report generator
        report_gen = ReportGenerator(
            output_dir="outputs/reports", temp_dir="outputs/temp"
        )

        # Generate report
        report_path = report_gen.generate_report(
            recommendation=recommendation,
            output_filename=None,  # Auto-generate filename
        )

        logger.info("=" * 60)
        logger.info("REPORT GENERATION COMPLETED")
        logger.info("=" * 60)
        logger.info(f"✓ PDF report generated: {report_path}")

        # Get file size
        file_size = Path(report_path).stat().st_size / 1024  # KB
        logger.info(f"✓ File size: {file_size:.1f} KB")

        logger.info("")
        logger.info("=" * 60)
        logger.info("ANALYSIS PIPELINE COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"✗ Analysis failed: {str(e)}", exc_info=True)
        raise


async def analyze_multiple_companies():
    """
    Example: Batch analysis of multiple companies.
    """

    companies = [
        ("AAPL", "Apple Inc."),
        ("MSFT", "Microsoft Corporation"),
        ("GOOGL", "Alphabet Inc."),
        ("AMZN", "Amazon.com Inc."),
        ("NVDA", "NVIDIA Corporation"),
    ]

    logger.info(f"Analyzing {len(companies)} companies...")

    for task_id, (ticker, company_name) in enumerate(companies):
        await main(
            task_id=f"analysis_{task_id + 1}", ticker=ticker, company_name=company_name
        )

    pass


if __name__ == "__main__":
    """
    Run the investment analysis pipeline.
    
    Usage:
        python example_usage.py
        
    Environment Variables:
        ANTHROPIC_API_KEY: Your Anthropic API key
    """

    # Run main analysis
    asyncio.run(main())

    # Optional: Run additional examples
    # asyncio.run(analyze_multiple_companies())
