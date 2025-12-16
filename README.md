# Project ai-financial-advisor

A practice repository to showcase Anthropic's Agent Skills in an area of great interest to me: financial investing.

The overall goal of this project is to develop an agentic AI framework that provides financial advisory regarding whether to invest or not in a particular publicly-traded company.

>  ⚠️ **Warning**: I am not a trained nor certified financial advisor, and the development of this tool is solely meant as a way for me to practice my skills in the area of agentic AI. Should you decide to use this tool, please remember that investing involves risks and its consequences are of the responsibility of the investor alone.

This project leverages the Agent Skills features described in [Claude Skills Cookbook](https://github.com/anthropics/claude-cookbooks/tree/ef506bc3de0d76f154cafb4dbb0f6a259c896ba2/skills). The main contributions of this project are as follows:

1. Creation of agentic AI framework with an orchestrator agent (i.e., an AI financial advisor) and its assistant AI agents that perform specific financial analyses under the guidance of their "supervisor" (the orchestrator agent).
2. Addition of a new agent skill for technical analysis of time-series financial data, leveraging [pandas_ta_classic](https://xgboosted.github.io/pandas-ta-classic/index.html#).

Note: This README is still under construction.

## Installation

1. Clone the repository

```shell
git clone git@github.com:bacalfa/ai-financial-advisor.git
cd ai-financial-advisor
```

2. Create virtual or a conda environment (example using `uv`)

```shell
uv init
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies (example using `uv`)

```shell
uv sync
```

4. Create file `.venv.example` in folder `.venv` containing the following text

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
```
