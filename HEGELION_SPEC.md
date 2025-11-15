# Hegelion Specification

## Overview

Hegelion is a dialectical reasoning system that processes queries through a structured three-phase workflow: Thesis → Antithesis → Synthesis. This document describes the theoretical framework, technical implementation, and output specifications.

## Theoretical Framework

### Dialectical Method

Hegelion implements a computational version of Hegelian dialectics:

1. **Thesis (Position)**: A comprehensive, well-reasoned answer that considers multiple perspectives
2. **Antithesis (Negation)**: A systematic critique that identifies contradictions, gaps, and alternative framings
3. **Synthesis (Sublation)**: A higher-level resolution that transcends the original contradiction

### Design Principles

1. **Always Synthesize**: Unlike traditional conflict-based systems, Hegelion always performs synthesis to encourage comprehensive reasoning
2. **Structured Contradictions**: Explicit identification and formalization of contradictions
3. **Research-Oriented**: Generation of testable predictions and research proposals
4. **Backend Agnostic**: Compatibility with multiple LLM providers
5. **Inspectable Traces**: Full visibility into the reasoning process

## Technical Architecture

### Core Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Thesis        │    │   Antithesis    │    │   Synthesis     │
│   Generation    │───▶│   Generation    │───▶│   Generation    │
│                 │    │                 │    │                 │
│ • Comprehensive │    │ • Contradiction │    │ • Transcendence │
│ • Multi-perspective│  │ • Gap analysis  │    │ • Novel framing │
│ • Well-structured│  │ • Alternative    │    │ • Research      │
│                 │    │   perspectives  │    │   proposals     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Prompt         │    │  Prompt         │    │  Prompt         │
│  Engineering    │    │  Engineering    │    │  Engineering    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LLM Backend Layer                            │
│  • OpenAI API    • Anthropic API    • Ollama    • Custom         │
└─────────────────────────────────────────────────────────────────┘
```

### Module Structure

- **`core.py`**: High-level public API (`run_dialectic`, `run_benchmark`)
- **`engine.py`**: Core dialectical reasoning engine
- **`backends.py`**: LLM provider abstractions
- **`parsing.py`**: Contradiction and research proposal extraction
- **`models.py`**: Data structures and Pydantic models
- **`prompts.py`**: Prompt templates for each phase
- **`config.py`**: Environment-driven configuration
- **`mcp_server.py`**: Model Context Protocol server implementation

## Output Schema

### Primary Output: HegelionResult

```json
{
  "query": "string",
  "mode": "synthesis",
  "thesis": "string",
  "antithesis": "string",
  "synthesis": "string",
  "contradictions": [
    {
      "description": "string",
      "evidence": "string (optional)"
    }
  ],
  "research_proposals": [
    {
      "description": "string",
      "testable_prediction": "string (optional)"
    }
  ],
  "metadata": {
    "thesis_time_ms": "number",
    "antithesis_time_ms": "number",
    "synthesis_time_ms": "number",
    "total_time_ms": "number",
    "backend_provider": "string",
    "backend_model": "string",
    "debug": {
      "internal_conflict_score": "number (optional)"
    }
  },
  "trace": {
    "thesis": "string",
    "antithesis": "string",
    "synthesis": "string",
    "contradictions_found": "number",
    "research_proposals": ["string"],
    "internal_conflict_score": "number (debug only)"
  }
}
```

### Contradiction Format

Contradictions are extracted in a structured format from the antithesis:

**Input Format (in Antithesis):**
```markdown
CONTRADICTION: [brief description]
EVIDENCE: [supporting evidence or reasoning]
```

**Output Format:**
```json
{
  "description": "Thesis assumes X without considering Y",
  "evidence": "Research shows that Y significantly impacts outcomes"
}
```

### Research Proposal Format

Research proposals are extracted from the synthesis:

**Input Format (in Synthesis):**
```markdown
RESEARCH_PROPOSAL: [description]
TESTABLE_PREDICTION: [falsifiable claim]
```

**Output Format:**
```json
{
  "description": "Investigate the relationship between X and Y",
  "testable_prediction": "Hypothesis: Increasing X will decrease Y by 20%"
}
```

### Benchmark JSONL Format

`run_benchmark` accepts either an in-memory sequence of prompt objects or a path to a JSONL file. Each line must contain either a string or a JSON object with a `query` or `prompt` field:

```jsonl
{"query": "How does climate change influence monsoon cycles?"}
{"prompt": "What strategic lessons came from the Apollo program?"}
"What was the lasting impact of the printing press?"
```

The function returns `list[HegelionResult]`. When an `output_file` is provided (CLI flag `--output` or API argument), results are also written as JSONL—one structured result per line that matches the primary output schema.

### MCP Tools

The MCP stdio server (`python -m hegelion.mcp_server`) publishes two tools:

1. **`run_dialectic`**
   - **Input schema**: `{ "query": string, "debug"?: boolean }`
   - **Output**: A single JSON object following the `HegelionResult` schema (pretty-printed in MCP responses). When `debug=true`, `metadata.debug` includes internal metrics such as conflict scores.

2. **`run_benchmark`**
   - **Input schema**: `{ "prompts_file": string, "debug"?: boolean }`
   - **Behavior**: Validates that the JSONL file exists, runs every prompt, and returns newline-delimited JSON (one result per line, identical to `HegelionResult.to_dict()`).

## Phase Specifications

### 1. Thesis Phase

**Objective**: Generate a comprehensive, multi-perspective answer

**Requirements**:
- Consider multiple viewpoints and approaches
- Be thorough but clear and well-structured
- Acknowledge uncertainty where appropriate
- Provide step-by-step reasoning before final answer

**Quality Criteria**:
- Breadth of perspective
- Logical coherence
- Evidence-based reasoning
- Clear structure

### 2. Antithesis Phase

**Objective**: Systematic critique of the thesis

**Requirements**:
- Find contradictions and logical gaps
- Identify unexamined assumptions
- Propose alternative framings
- Find edge cases where thesis breaks down
- Use structured contradiction format

**Quality Criteria**:
- Intellectual honesty (adversarial but fair)
- Specific, actionable critiques
- Evidence-based challenges
- Alternative perspectives

### 3. Synthesis Phase

**Objective**: Higher-level resolution transcending both thesis and antithesis

**Requirements**:
- Must transcend (not just combine) original positions
- Cannot simply say "thesis is right" or "antithesis is right"
- Cannot say "both have merit" without deeper insight
- Should offer genuinely novel perspective
- Should be more sophisticated than either original position
- Encouraged to include research proposals

**Quality Criteria**:
- Novelty of perspective
- Logical transcendence
- Testability of insights
- Research relevance

## Internal Conflict Scoring

While conflict scores are not exposed in the main API (to encourage human judgment), they are computed internally for research purposes:

### Scoring Components

1. **Semantic Distance (40%)**: Cosine similarity between thesis and antithesis embeddings
2. **Contradiction Signal (30%)**: Based on number and quality of extracted contradictions
3. **Normative Conflict (30%)**: LLM-based assessment of fundamental disagreement

### Scoring Scale

- **0.0-0.2**: Minimal conflict (complementary positions)
- **0.2-0.4**: Low conflict (minor tensions)
- **0.4-0.6**: Moderate conflict (meaningful disagreements)
- **0.6-0.8**: High conflict (significant tensions)
- **0.8-1.0**: Very high conflict (fundamental opposition)

### Accessing Internal Scores

Internal conflict scores are available in debug mode:

```python
result = await run_dialectic(query, debug=True)
conflict_score = result.metadata["debug"]["internal_conflict_score"]
```

## Backend Configuration

### Environment Variables

Default `.env` configuration (and the library's code defaults) use Anthropic Claude Sonnet:

```bash
HEGELION_PROVIDER=anthropic
HEGELION_MODEL=claude-4.5-sonnet-latest
```

Override the provider/model when evaluating other backends:

**Anthropic / Claude (recommended default):**
```bash
HEGELION_PROVIDER=anthropic
HEGELION_MODEL=claude-4.5-sonnet-latest
ANTHROPIC_API_KEY=your-anthropic-api-key-here
# Override only if you proxy the API
# ANTHROPIC_BASE_URL=https://api.anthropic.com
```

**OpenAI:**
```bash
HEGELION_PROVIDER=openai
HEGELION_MODEL=gpt-4.1
OPENAI_API_KEY=your-openai-api-key-here
# OPENAI_BASE_URL=https://api.openai.com/v1
```

> Tested baselines: `gpt-4.1` (chat/completions, recommended) and `gpt-4.1-mini` (lower-cost baseline) both complete the Thesis → Antithesis → Synthesis loop without tweaks.

**Custom HTTP backend (advanced):**
```bash
HEGELION_PROVIDER=custom_http
HEGELION_MODEL=your-custom-model-id
CUSTOM_API_BASE_URL=https://your-endpoint.example.com/v1/run
CUSTOM_API_KEY=your-custom-api-key
# CUSTOM_API_TIMEOUT=60.0
```

**Ollama (local experiments):**
```bash
HEGELION_PROVIDER=ollama
HEGELION_MODEL=llama3.1
OLLAMA_BASE_URL=http://localhost:11434
```

Optional engine settings:

```bash
HEGELION_MAX_TOKENS_PER_PHASE=10000
```

### Backend Support

1. **Anthropic**: Claude models via the official Anthropic API
2. **OpenAI**: GPT models via OpenAI API or compatible endpoints
3. **Custom HTTP**: Minimal JSON HTTP bridge for bespoke providers
4. **Ollama**: Local models via the Ollama HTTP API

## Research Applications

### Evaluation Metrics

1. **Contradiction Quality**: Assess specificity and relevance of identified contradictions
2. **Synthesis Novelty**: Evaluate originality and transcendence of synthesis
3. **Research Proposals**: Measure testability and relevance of generated research ideas
4. **Temporal Consistency**: Analyze reasoning patterns across multiple queries
5. **Cross-Model Comparison**: Compare outputs across different LLM backends

### Benchmark Categories

1. **Factual**: Questions with verifiable answers
2. **Scientific**: Complex scientific concepts and theories
3. **Historical**: Historical events and interpretations
4. **Philosophical**: Abstract and conceptual questions
5. **Ethical**: Moral and value-laden dilemmas

### Analysis Dimensions

1. **Reasoning Depth**: Complexity and sophistication of dialectical moves
2. **Contradiction Detection**: Accuracy and relevance of identified tensions
3. **Synthesis Quality**: Novelty and coherence of resolutions
4. **Research Value**: Practical relevance and testability of proposals
5. **Consistency**: Reliability across different queries and contexts

## Usage Patterns

### AI Alignment Research

- Analyze tensions in safety proposals
- Identify hidden assumptions in alignment strategies
- Generate novel research directions
- Stress-test ethical frameworks

### Academic Research

- Explore hypotheses and counterarguments
- Identify research gaps and opportunities
- Generate literature review insights
- Propose experimental designs

### Strategic Planning

- Challenge business assumptions
- Identify strategic risks and opportunities
- Generate innovative solutions
- Explore alternative scenarios

### Education

- Teach critical thinking and argumentation
- Demonstrate dialectical reasoning
- Explore complex topics systematically
- Develop research skills

## Performance Considerations

### Latency

Typical processing times per query:
- **Thesis**: 1-3 seconds
- **Antithesis**: 2-4 seconds
- **Synthesis**: 2-5 seconds
- **Total**: 5-12 seconds (varies by model and query complexity)

### Cost

Three-phase processing increases API costs approximately 3x compared to single-pass generation. Consider using for high-value queries where dialectical depth is important.

### Quality Factors

1. **Model Capability**: More sophisticated models generate better contradictions and syntheses
2. **Query Complexity**: Rich, ambiguous queries yield more interesting dialectical analysis
3. **Domain Knowledge**: Results vary by model's training in relevant domains
4. **Prompt Engineering**: Careful prompt design improves phase quality

## Future Directions

### Planned Enhancements

1. **Multi-Expert Synthesis**: Multiple models contributing to synthesis generation
2. **Session-Level Continuity**: Maintaining dialectical context across multiple queries
3. **Domain-Specific Templates**: Specialized prompts for different fields
4. **Quality Metrics**: Automated assessment of output quality
5. **Interactive Mode**: User feedback during dialectical process

### Research Opportunities

1. **Synthesis Evaluation**: Developing metrics for synthesis quality
2. **Cross-Cultural Analysis**: Comparing dialectical patterns across cultural contexts
3. **Pedagogical Applications**: Using Hegelion for teaching critical thinking
4. **Collaborative Intelligence**: Human-AI dialectical collaboration
5. **Ethical Frameworks**: Systematic ethical analysis using dialectical methods

## Contributing

### Development Guidelines

1. **Backward Compatibility**: Maintain API stability when adding features
2. **Test Coverage**: Ensure comprehensive tests for new functionality
3. **Documentation**: Update specifications and examples for changes
4. **Research Validation**: Validate improvements through systematic testing
5. **Security**: Follow secure coding practices, especially for API credentials

### Quality Standards

1. **Contradiction Extraction**: Robust parsing of various contradiction formats
2. **Research Proposal Identification**: Accurate extraction of testable predictions
3. **Error Handling**: Graceful degradation when LLM backends fail
4. **Performance**: Efficient processing and minimal latency
5. **Security**: Proper handling of sensitive information and API keys

This specification serves as the authoritative reference for Hegelion's design, implementation, and usage patterns.
