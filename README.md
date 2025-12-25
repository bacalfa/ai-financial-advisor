# Project ai-financial-advisor

A practice repository to showcase Anthropic's Agent Skills in an area of great interest to me: financial investing.

The overall goal of this project is to develop an agentic AI framework that provides financial advisory regarding whether to invest or not in a particular publicly-traded company.

>  ⚠️ **Warning**: I am not a trained nor certified financial advisor, and the development of this tool is solely meant as a way for me to practice my skills in the area of agentic AI. Should you decide to use this tool, please remember that investing involves risks and its consequences are of the responsibility of the investor alone.

This project is inspired by and leverages the Agent Skills features described in [Claude Skills Cookbook](https://github.com/anthropics/claude-cookbooks/tree/ef506bc3de0d76f154cafb4dbb0f6a259c896ba2/skills). The main contributions of this project are as follows:

1. Creation of agentic AI framework with an orchestrator agent (i.e., an AI financial advisor) and its assistant AI agents that perform specific financial analyses under the guidance of their "supervisor" (the orchestrator agent).
2. Addition of a new agent skill for technical analysis of time-series financial data, leveraging [pandas_ta_classic](https://xgboosted.github.io/pandas-ta-classic/index.html#).


## Financial Assistants

Three types of agents acting as financial assistants to an experienced financial advisor are implemented. Each type performs one of the following financial analyses.

### Financial Statements

AI assistant analyzes income statements, balance sheets, and cash flow statements to assess financial health. Adapted from Anthropic's cookbook. Key evaluations:

- Evaluates income statements, balance sheets, cash flows
- Calculates key financial ratios
- Agent Skills for retrieving financial data
- Outputs health scores and trend analysis

For more details on the sill description, see [src/skills/analyzing-financial-statements/SKILL.md](src/skills/analyzing-financial-statements/SKILL.md).


### Financial Modeling

AI assistant builds Discounted Cash Flow (DCF) models, performs comparable company analysis, and conducts sensitivity analysis. Adapted from Anthropic's cookbook. Key calculations:

- DCF valuation
- Comparable company analysis
- Sensitivity analysis
- Agent Skills for Weighted Average Cost of Capital (WACC) calculation, Free Cash Flow (FCF) projections, terminal value

For more details on the sill description, see [src/skills/financial-modeling-valuation/SKILL.md](src/skills/financial-modeling-valuation/SKILL.md).

*Note: Automatically list comparable companies using a (free) [Massive](https://massive.com/) API key for stocks. See section [Installation](#installation).*

### Technical Analysis

AI assistant performs technical analysis using pandas_ta_classic library for comprehensive indicator calculations and trading signal generation. **NEW: Original skill created for this project**. Key features:
- Uses `pandas_ta_classic` for technical indicators
- Analyzes trends, momentum, volume, volatility
- Identifies support/resistance levels and chart patterns
- Agent Skills for calculating indicators and detecting patterns
- Outputs trading signals and entry/exit points

For more details on the sill description, see [src/skills/technical-analysis/SKILL.md](src/skills/technical-analysis/SKILL.md).


## Financial Advisor (Orchestrator)

Class `FinancialAdvisor` represents a senior financial advisor that acts as an orchestrator agent. The main features of this agent include:
- Coordinates all assistant agents (parallel or sequential)
- Implements judgment layer with configurable weights
- Feedback loops for improving low-confidence results
- Class `InvestmentRecommendation`: Comprehensive recommendation dataclass
- Synthesis logic combining fundamental, technical, and consistency scores

The figure below shows the complete flow from user query through orchestrator, specialized agents with skills, judgment layer, and report generation. Note the feedback loop that allows the orchestrator to request additional analysis if needed.

![Financial advisor architecture diagram](imgs/financial_advisor_architecture.png)


## Financial Report Generation

*🚧 To be implemented*

The sophisticated multi-agent AI system culminates in a professional financial PDF report generation including the following features:
- Complete sections: Cover, Executive Summary, Financial Analysis, Valuation, Technical Analysis, Risk Assessment, Conclusion, Disclaimer
- Professional tables with color-coded recommendations
- Proper formatting and layout


## Installation

1. Clone the repository

```shell
git clone git@github.com:bacalfa/ai-financial-advisor.git
cd ai-financial-advisor
```

2. Create virtual or a conda environment (example using `uv`)

```shell
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies (example using `uv`)

```shell
uv sync
```

4. Create file `.env` in top folder and containing the following text

```
# Create this file in .env and add your actual API key

# Required: Your Anthropic API key from https://console.anthropic.com/
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Model selection (Skills require Claude 4.5 Sonnet or newer)
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929

# Optional: Custom skills storage directory (default: ./src/agents/custom_skills)
SKILLS_STORAGE_PATH=./src/agents/custom_skills

# Optional: Output directory for generated files (default: ./outputs)
OUTPUT_PATH=./outputs

# Massive API key from https://massive.com/ (optional)
MASSIVE_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## Usage

### Financial Statement Example

Run script [examples/financial_statements_example.py](examples/financial_statements_example.py) to obtain the financial statement analysis by an AI agent for the company Apple (AAPL). The `response` result will look something like the following:

![Example of financial statement output for AAPL](imgs/financial_statements_example.png)

The core of the agent's response is available in field `data`, which in addition to a "health score" as assessed by the agent, also includes:

- Key metrics

![Example of financial statement output for AAPL: key metrics](imgs/financial_statements_example_key_metrics.png)

- Trend analysis

![Example of financial statement output for AAPL: trend analysis](imgs/financial_statements_example_trend_analysis.png)

- Strengths

![Example of financial statement output for AAPL: strengths](imgs/financial_statements_example_strengths.png)

- Concerns

![Example of financial statement output for AAPL: concerns](imgs/financial_statements_example_concerns.png)

- Risks

![Example of financial statement output for AAPL: risks](imgs/financial_statements_example_risks.png)

- Data quality notes

```python
'Financial data is complete for 2022-2025 period. Interest expense data missing for 2024-2025, using 2023 data for coverage ratio. High quality data from reliable sources.'
```

- Health score notes

```python
"Score of 0.76 reflects Apple's exceptional profitability (net margin 26.9%), solid growth trajectory, but considers liquidity constraints from negative working capital structure and moderate leverage levels. Strong cash generation and market position support overall health."
```


Note that this is only one independent financial analysis performed by an AI agent.


### Financial Modeling Example

Run script [examples/financial_models_example.py](examples/financial_models_example.py) to obtain the financial modeling analysis by an AI agent for the company Apple (AAPL). The `response` result will look something like the following:

![Example of financial modeling output for AAPL](imgs/financial_models_example.png)

The core of the agent's response is available in field `data` which contains calculation and analysis results:

![Example of financial modeling output for AAPL: data](imgs/financial_models_example_data.png)


### Technical Analysis Example

Run script [examples/financial_ta_example.py](examples/financial_ta_example.py) to obtain the financial technical analysis by an AI agent for the company Apple (AAPL). The `response` result will look something like the following:

![Example of financial technical analysis output for AAPL](imgs/financial_ta_example.png)

The core of the agent's response is available in field `data` which contains calculation and analysis results:

![Example of financial technical analysis output for AAPL: data](imgs/financial_ta_example_data.png)

The agent also summarizes its rationale for the "technical score":

```python
'Score of 0.70 reflects mixed technical picture: bullish trend structure (SMA alignment) and volume (OBV) offset by weak momentum indicators (oversold stochastic, negative MACD histogram). Moderate risk tolerance suggests cautious approach given conflicting signals.'
```


### Financial Advisor Example

Run script [examples/financial_advisor_example.py](examples/financial_advisor_example.py) to obtain an investment recommendation of the company Apple (AAPL) by an AI financial advisor agent and its financial assistant agents. The `response` result will look something like the following:

![Example of financial advisor analysis output for AAPL](imgs/financial_advisor_example.png)

The core of the agent's response is available in field `data` which contains calculation and analysis results:

![Example of financial advisor analysis output for AAPL: data](imgs/financial_advisor_example_data.png)
