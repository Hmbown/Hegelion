# Hegelion

[![CI](https://github.com/Shannon-Labs/Hegelion/actions/workflows/ci.yml/badge.svg)](https://github.com/Shannon-Labs/Hegelion/actions/workflows/ci.yml)

> A dialectical reasoning harness for LLMs: Thesis → Antithesis → Synthesis with structured contradictions, research proposals, and metadata you can trust.

Hegelion runs any LLM through Thesis → Antithesis → Synthesis and ships the full result as structured JSON (`HegelionResult`). You always get the three passages plus contradictions, research proposals, and metadata (timings, backend info, optional debug trace). The default backend is Anthropic Claude Sonnet, but the same loop works with OpenAI, Ollama, or a custom HTTP endpoint.

- **Always synthesizes** – every query completes the full loop.
- **Structured output** – contradictions and proposals arrive as lists, ready for scoring.
- **Honest provenance** – backend/model/timings live in `metadata`, internal scores only appear under `metadata.debug` when requested.
- **Tooling included** – CLI (`hegelion`, `hegelion-bench`) and MCP server (`hegelion-server`) come with the package.

## Install

### Requirements

- Python 3.10+ (regularly tested on 3.10 and 3.11)
- `uv` recommended for dependency management (fallback: `pip install -e .`)

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/Shannon-Labs/Hegelion.git
   cd Hegelion
   ```

2. **Install dependencies** (prefer `uv`)
   ```bash
   uv sync              # creates .venv and installs runtime deps
   ```

   Alternative with pip:
   ```bash
   pip install -e .
   ```

   > **Note:** Hegelion is currently a Git-first research release; PyPI packaging will come later.

## Configure

1. **Copy the environment template**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your preferred backend**

   For Anthropic Claude (default):
   ```bash
   HEGELION_PROVIDER=anthropic
   HEGELION_MODEL=claude-4.5-sonnet-latest
   ANTHROPIC_API_KEY=your-anthropic-api-key-here
   ```

   For OpenAI:
   ```bash
   HEGELION_PROVIDER=openai
   HEGELION_MODEL=gpt-4.1
   OPENAI_API_KEY=your-openai-api-key-here
   ```

   For Ollama (local):
   ```bash
   HEGELION_PROVIDER=ollama
   HEGELION_MODEL=llama3.1
   OLLAMA_BASE_URL=http://localhost:11434
   ```

   For Custom HTTP backend:
   ```bash
   HEGELION_PROVIDER=custom_http
   HEGELION_MODEL=your-model-id
   CUSTOM_API_BASE_URL=https://your-endpoint.example.com/v1/run
   CUSTOM_API_KEY=your-custom-api-key
   ```

## Run

### Command Line Interface

```bash
# Single query with readable summary
hegelion "Can AI be genuinely creative?" --format summary

# Raw JSON result (handy for scripting)
hegelion "Explain what photosynthesis does for a plant." --debug --format json

# JSONL benchmark (one prompt per line)
hegelion-bench benchmarks/examples_basic.jsonl --output runs.jsonl --summary
```

### Python API

```python
import asyncio
from hegelion import run_dialectic, run_benchmark

async def main():
    result = await run_dialectic("Is privacy more important than security?", debug=True)
    print(result.synthesis)
    print(f"Contradictions: {len(result.contradictions)}")
    print(f"Research proposals: {len(result.research_proposals)}")

asyncio.run(main())
```

## Integrate with Claude Desktop

Add Hegelion as an MCP server in Claude Desktop by configuring your `claude_desktop_config.json` file:

```json
{
  "mcpServers": {
    "hegelion": {
      "command": "hegelion-server",
      "args": [],
      "cwd": "/path/to/Hegelion",
      "env": {
        "HEGELION_PROVIDER": "anthropic",
        "HEGELION_MODEL": "claude-4.5-sonnet-latest",
        "ANTHROPIC_API_KEY": "your-anthropic-api-key-here"
      }
    }
  }
}
```

> **Note:** If `hegelion-server` isn't on PATH, use `python -m hegelion.mcp_server` as the command instead.

### MCP Tools

Hegelion MCP server exposes the following tools:

#### `run_dialectic`
Process a query using Hegelian dialectical reasoning (thesis → antithesis → synthesis). Always performs synthesis to generate comprehensive reasoning. Returns structured contradictions and research proposals.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "The question or topic to analyze dialectically"
    },
    "debug": {
      "type": "boolean",
      "description": "Include debug information and internal conflict scores",
      "default": false
    }
  },
  "required": ["query"]
}
```

#### `run_benchmark`
Run Hegelion on multiple prompts from a JSONL file. Each line should contain a JSON object with a 'prompt' or 'query' field. Returns newline-delimited JSON, one HegelionResult per line.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "prompts_file": {
      "type": "string",
      "description": "Path to JSONL file containing prompts (one per line)"
    },
    "debug": {
      "type": "boolean",
      "description": "Include debug information and internal conflict scores",
      "default": false
    }
  },
  "required": ["prompts_file"]
}
```

## Hero Example

Example output for "Can AI be genuinely creative?" using glm-4.6 backend:

```json
{
  "query": "Can AI be genuinely creative?",
  "mode": "synthesis",
  "thesis": "THESIS: The Creative Machine ...",
  "antithesis": "ANTITHESIS: The Sophisticated Mirror ...",
  "synthesis": "SYNTHESIS: The Co-Creative Process and the Emergence of Synthetic Subjectivity ...",
  "contradictions": [
    {
      "description": "The Redefinition Fallacy",
      "evidence": "The thesis narrows 'creativity' to a computable procedure, ignoring intent and subjective urgency."
    },
    {
      "description": "The Stochastic Parrot Illusion",
      "evidence": "Interpolation cannot generate the domain-breaking novelty the thesis cites as proof."
    },
    {
      "description": "Dismissing Intent as a Category Error",
      "evidence": "Removing the creator's context impoverishes art; model objective functions are not creative will."
    }
  ],
  "research_proposals": [
    {
      "description": "The Co-Creative Trace Analysis",
      "testable_prediction": "Iterative human–AI dialogues produce artifacts judged more creative than single-pass outputs."
    }
  ],
  "metadata": {
    "backend_provider": "AnthropicLLMBackend",
    "backend_model": "glm-4.6",
    "total_time_ms": 37564.40,
    "debug": {
      "internal_conflict_score": 0.95
    }
  }
}
```

## Quick Start with Another AI

If you'd like to have another AI assistant set up Hegelion for you, use this prompt:

```
Please clone https://github.com/Shannon-Labs/Hegelion, run `uv sync`, copy `.env.example`, set Anthropic keys, and start `hegelion-server`. Confirm `hegelion --help` works.
```

## Examples & Benchmarks

- `examples/glm4_6_examples.jsonl` — canonical glm-4.6 traces for:
  - Philosophical: "Can AI be genuinely creative?"
  - Factual: "What is the capital of France?"
  - Scientific: "Explain what photosynthesis does for a plant."
  - Historical: "When was the first moon landing?"
- `examples/README.md` — index + CLI instructions for replaying each example.
- `examples/*.md` — narrative walk-throughs for creative reasoning prompts.
- `benchmarks/examples_basic.jsonl` — starter JSONL for benchmarking harness behavior.

Generate your own dataset by adding `--output my_runs.jsonl` to either CLI or by calling `run_benchmark(..., output_file="file.jsonl")` from Python.

## For Model Builders & Evaluation Teams

1. Switch providers by editing `.env` (`HEGELION_PROVIDER` + `HEGELION_MODEL`).
2. Run benchmarks via `hegelion-bench prompts.jsonl --output results.jsonl`, then rerun with other providers for apples-to-apples comparison.
3. Parse the JSONL output—each line already includes thesis/antithesis/synthesis, contradictions, proposals, metadata, and (optionally) debug metrics.

## Development

```bash
# Install dev extras
uv sync --dev

# Lint / tests
uv run pytest -v

# Optional: run CLI smoke tests
uv run hegelion --help
uv run hegelion-bench --help

# (Optional) install pre-commit hooks
uv run pre-commit install
```

## License & Status

- **License:** MIT (see `LICENSE`).
- **Status:** Actively maintained research infrastructure. The dialectical protocol and JSON schema are stable; internal engine/backends may evolve.
