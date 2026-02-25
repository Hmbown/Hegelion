# Changelog

## 0.5.0 – Maintenance Refresh (February 2026)

### Added
- **Python 3.13 support**: Added to CI test matrix and pyproject classifiers
- **PEP 561 `py.typed` marker**: Enables type-checker support for library consumers
- **Public API exports**: `hegelion.__init__` now exports key classes (`DialecticalPrompt`, `PromptDrivenDialectic`, `AutocodingPrompt`, `PromptDrivenAutocoding`, `AutocodingState`, and workflow helpers)
- **`--version` flag**: Both `hegelion-server` and `hegelion-setup-mcp` CLIs now support `--version`

### Changed
- **Updated model references**: `.env.example` now references current models (Claude Sonnet 4.6, GPT-5.2, Gemini 3 Pro)

### Fixed
- **CHANGELOG formatting**: Corrected malformed duplicate 0.3.0 / 0.2.3 section header
- **README staleness**: "Recent Changes" section now includes v0.4.5 and v0.4.6

## 0.4.6 – CI Fix & Automated Releases (February 4, 2026)

### Fixed
- Fixed CI pipeline and automated release workflow

## 0.4.5 – Optional CLI Execution for `dialectical_single_shot` (February 4, 2026)

### Added
- **Single-call CLI execution** for `dialectical_single_shot`: `execute`, `timeout_seconds`, `max_retries`, plus env-based configuration (`HEGELION_LLM_COMMAND_JSON`, `HEGELION_LLM_COMMAND`, `HEGELION_MCP_AUTO_EXECUTE=1`)
- **`hegelion-setup-mcp` flags**: `--llm-command-json`, `--llm-command`, `--auto-execute` to configure CLI execution via MCP host config

## 0.4.4 – Simplified Skill & Command (January 21, 2026)

### Changed
- Condensed `/hegelion` slash command and Codex skill to minimal routing tables
- Removed verbose manual workflows in favor of MCP-first approach

## 0.4.3 – MCP Refactor + Codex Skill (January 12, 2026)

### Added
- **Codex skill**: Added `skills/hegelion/SKILL.md` for the `/hegelion` workflow

### Changed
- Refactored MCP server into tooling, handlers, validation, and response helpers

## 0.4.2 – Unified /hegelion Command (January 2026)

### Added
- **`/hegelion` command**: Single entry point for both dialectical and autocoding workflows
- **Host shortcuts**: `hegelion-setup-mcp --host claude-desktop|cursor|vscode|windsurf`

### Changed
- Consolidated separate autocoding command and skill into unified `/hegelion`
- Code formatted with black

## 0.4.1 – Schema Versioning (December 2025)

### Added
- **Schema versioning**: All structured outputs include `schema_version`
- **Phase clarity**: `player_prompt` and `coach_prompt` include `current_phase` and `next_phase`
- **Error handling**: Invalid transitions return structured errors with `expected`, `received`, `hint`

## 0.4.0 – Autocoding System (December 2025)

### Added
- **Player-Coach loop**: Dialectical autocoding based on Block AI's g3 agent research
- **MCP tools**: `autocoding_init`, `player_prompt`, `coach_prompt`, `autocoding_advance`
- **Session persistence**: `autocoding_save` / `autocoding_load`
- **Single-shot mode**: `autocoding_single_shot` for simpler tasks
- **Brand entrypoint**: `hegelion` tool with `mode` parameter

## 0.3.2 – MCP Server Simplification

### Removed
- **MCP `run_dialectic` tool:** Removed the server-side execution tool that required LLM API configuration. Users on Cursor, Claude Desktop, VS Code, etc. should use `dialectical_single_shot` or `dialectical_workflow` instead—these generate prompts that your editor's LLM executes directly, with no API keys needed.

### Changed
- **Updated `mcp_instructions.md`:** Documentation now guides agents to use prompt-generation tools (`dialectical_single_shot`, `dialectical_workflow`) rather than server-side execution.

### Why This Change
The `run_dialectic` MCP tool required server-side API keys (e.g., `HEGELION_PROVIDER`, `ANTHROPIC_API_KEY`), which was confusing for MCP users who expected a zero-config experience. The prompt-generation tools provide the same dialectical reasoning without any server-side LLM configuration.

---

## 0.3.1 – Response Styles & Gemini CLI Extension Support

### Added
- **New Response Styles:** Added two new response formats for dialectical workflows:
  - `conversational`: Natural dialogue format with smooth transitions like "but on the other hand..." and "so perhaps the best way forward is..."
  - `bullet_points`: Concise bullet-point format with clearly marked Thesis, Antithesis, and Synthesis sections for quick scanning
  - Full compatibility with existing `json`, `sections`, and `synthesis_only` styles
- **New: Gemini CLI Extension:** Added official support for the Gemini CLI. You can now install Hegelion directly as an extension to use dialectical tools within your Gemini CLI workflows.
- **New: `GEMINI.md` Context:** Included a persistent context file to guide the Gemini model on how to use Hegelion's dialectical tools effectively.

## 0.3.0 – Model-Agnostic Support & Feature Expansion

- **New: Model-Agnostic MCP Server:** Introduced `hegelion-prompt-server` which allows using Hegelion with *any* model configured in your editor/IDE (Cursor, VS Code, Claude Desktop) without needing API keys.
- **New: Persona-Based Critiques:** Configure specific personas for the antithesis phase (e.g., "Council of Critics," "Security Engineer," "Ruthless Editor") via the Python API.
- **New: Iterative Refinement:** Support for looping the dialectical process (Synthesis Round 1 → Thesis Round 2) for deeper analysis.
- **New: Search Grounding:** Instruct models to verify claims with search tools during the antithesis phase.
- **Changed:** The `hegelion` CLI is now primarily a demo/summary tool. Advanced workflows (personas, iterations) are available via the Python API and MCP servers.
- **Documentation:** Comprehensive rewrite of README and documentation to emphasize the dual-path usage (Prompt-Based vs. API-Based).

## 0.2.3 – MCP/assistant integration polish

- Clarified canonical `HegelionResult` JSON schema in `README.md`, including backend and timing fields, and documented when `trace` and `metadata.debug` appear.
- Expanded `docs/MCP.md` with friendly request/response examples for `run_dialectic` and `run_benchmark`, plus explicit assistant-integration guidance for parsing JSON and JSONL outputs.
- Aligned README/MCP documentation with the actual `HegelionResult` schema used by the core engine, CLI, and MCP server to ensure AI assistants see a single, stable contract.

---

## 0.2.2+phase2 – Search-Grounded Dialectics with Council and Judge

**🎉 MAJOR RELEASE: Advanced Dialectical Reasoning System**

### ✨ **New Phase 2 Features**

#### 🔍 **Search-Grounded Antithesis**
- **Smart Search Providers**: Automatic fallback from Tavily (premium) to DuckDuckGo (free)
- **Real-World Grounding**: Antithesis phases can now access current information via web search
- **Context Integration**: Search results are seamlessly woven into dialectical reasoning

#### 👥 **The Council - Multi-Perspective Critiques**  
- **Three Expert Perspectives**:
  - **The Logician**: Formal reasoning and logical consistency
  - **The Empiricist**: Evidence, facts, and empirical grounding  
  - **The Ethicist**: Ethical implications and societal impact
- **Concurrent Processing**: Multiple critiques generated simultaneously via async
- **Unified Synthesis**: All council perspectives integrated into final reasoning

#### ⚖️ **The Iron Judge - Quality Evaluation**
- **Structured Scoring**: 0-10 quality assessment with detailed reasoning
- **Instructor Integration**: Guaranteed structured output using Pydantic models
- **Iterative Improvement**: Automatic retry for low-quality results
- **Critique Validity**: Assessment of whether antithesis critiques were properly addressed

### 🛠️ **Enhanced APIs**

#### **Core API Enhancements**
```python
# Phase 2 Enhanced Dialectics
result = await run_dialectic(
    query="Your question",
    use_search=True,        # Web search grounding
    use_council=True,       # Multi-perspective critiques  
    use_judge=True,         # Quality evaluation
    min_judge_score=7,      # Quality threshold
    max_iterations=3        # Automatic improvement
)
```

#### **MCP Server Phase 2 Support** 
- Updated `run_dialectic` tool with all Phase 2 parameters
- Enhanced Claude Desktop integration with search and council features
- Structured quality evaluation for AI assistant workflows

### 📦 **New Dependencies**
- `duckduckgo-search>=6.0.0` - Free web search (no API key required)
- `instructor>=1.0.0` - Structured LLM output with Pydantic
- `pydantic>=2.0.0` - Enhanced data validation and parsing
- **Optional**: `tavily-python>=0.3.0` - Premium search for professional use

### 🏗️ **Architecture Improvements**
- **Modular Phase 2**: Search, council, and judge features are optional and imported on-demand
- **Graceful Degradation**: Falls back to Phase 1 standard dialectics if Phase 2 dependencies unavailable
- **Enhanced Metadata**: Judge scores, council perspectives, and search context in debug traces
- **Quality Assurance**: Automatic retries and quality thresholds for production use

### 🔧 **Technical Details**
- **Backward Compatible**: All existing APIs continue to work unchanged
- **Performance**: Phase 2 features add ~2-5x processing time but deliver significantly richer analysis
- **Error Handling**: Robust fallbacks ensure system never fails due to Phase 2 enhancements
- **Caching**: Phase 2 results are fully cacheable with enhanced cache keys

### 💡 **Usage Examples**

**Search-Enhanced Analysis**:
```python
# Ground dialectics in current information
result = await run_dialectic(
    "What are the latest developments in quantum computing?",
    use_search=True
)
```

**Multi-Perspective Council Critique**:
```python  
# Get logical, empirical, AND ethical perspectives
result = await run_dialectic(
    "Should we implement universal basic income?",
    use_council=True,
    council_members=["The Logician", "The Ethicist"]
)
```

**Quality-Assured Reasoning**:
```python
# Ensure high-quality output with automatic improvement
result = await run_dialectic(
    "Explain consciousness and free will",
    use_judge=True,
    min_judge_score=8,
    max_iterations=3
)
```

**Full Phase 2 Stack**:
```python
# The complete enhanced dialectical experience
result = await run_dialectic(
    "How should humanity approach artificial general intelligence?",
    use_search=True,      # Current information
    use_council=True,     # Multiple expert perspectives
    use_judge=True,       # Quality assurance
    min_judge_score=7,    # High quality threshold
    max_iterations=2,     # Improvement iterations
    debug=True           # Full diagnostic trace
)
```

This release transforms Hegelion from a basic dialectical reasoner into a sophisticated multi-agent reasoning system with real-world grounding and quality assurance.

## 0.2.2 – MCP documentation and GLM backend verification

- Added comprehensive MCP reference guide (`docs/MCP.md`) with tool schemas, troubleshooting, and client integration notes
- Added Claude Desktop configuration example (`examples/mcp/claude_desktop_config.json`)
- Verified GLM 4.6 backend via OpenAI-compatible endpoint (Z.AI devpack)
- Enhanced documentation with verified backends section and log-sharing guidance
- Improved README with MCP quick start and backend verification details
- Fixed package discovery in `pyproject.toml` to exclude `logs/` directory from builds

## 0.2.1 – License format fix

- Fixed deprecated license format in `pyproject.toml` (changed from table to SPDX string format)
- Removed deprecated license classifier

## 0.2.0 – First public release

- Refactored into a clean `hegelion` Python package with clear module boundaries (core, engine, backends, parsing, models, prompts, config, MCP server).
- Introduced `HegelionResult` with structured contradictions, research proposals, and provenance metadata.
- Added CLI tools: `hegelion` for single queries and `hegelion-bench` for JSONL benchmarks.
- Implemented MCP server (`hegelion-server`) exposing `run_dialectic` and `run_benchmark` tools.
- Wrote comprehensive README and `HEGELION_SPEC.md` describing the protocol and JSON schema.
- Added test suite, pre-commit hooks, and GitHub Actions CI for automated testing.
