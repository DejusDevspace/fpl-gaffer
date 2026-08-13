# ⚽ FPL Gaffer

> Your AI-powered Fantasy Premier League co-manager with data-driven insights, transfer suggestions, and tactical advice, delivered straight to you on WhatsApp.

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Status](https://img.shields.io/badge/Status-In%20Progress-yellow.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

**FPL Gaffer** is an agentic AI assistant for Fantasy Premier League managers. It combines real-time FPL data, expert/scout analysis, and a self-validating response loop to give you advice that's grounded in actual numbers, not guesswork.

Built on [LangGraph](https://github.com/langchain-ai/langgraph) with native tool-calling, it reasons about what data it needs, fetches it, validates its own answer, and delivers a WhatsApp-friendly plain-text response.

### What makes it different

- **Never hallucinates** - every claim is checked against the tool results that produced it
- **Self-validates** - a dedicated validation node catches unsupported claims before they reach you
- **Speaks FPL** - differentials, punts, fixture swings, captaincy calls, not corporate chatbot language
- **WhatsApp-native** - plain text, short and punchy, designed for mobile
- **Cost-controlled** - per-turn tool-call budgets, turn compaction, and token-based summarization keep context lean

## Architecture

### Graph Topology

```
context_injection → agent_node ⟷ tool_node
                         ↓
               response_validation → compact_turn → (summarize | END)
                         ↓
                   retry_response → agent_node
```

| Node                          | Role                                                                                                         |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------ |
| `context_injection_node`      | Loads user/gameweek data, resolves per-user limits, resets turn counter                                      |
| `agent_node`                  | LLM turn — calls tools or produces a final answer. Unbinds tools when budget is exhausted                    |
| `tool_node`                   | `ToolNode(TOOLS, handle_tool_errors=True)` — executes tool calls, loops back to agent                        |
| `response_validation_node`    | Checks the final answer for hallucinations against this turn's tool results. Skipped when no tools were used |
| `compact_turn_node`           | Strips intermediate tool messages from history, keeping only the question and answer                         |
| `summarize_conversation_node` | Compresses history when estimated token count exceeds threshold                                              |
| `retry_response_node`         | Flags the next agent pass as a retry with validation feedback                                                |

### State

```python
class WorkflowState(MessagesState):
    user_id: str
    user_data: Dict[str, Any]
    gameweek_data: Dict

    response: str
    summary: str

    is_retry: bool
    retry_count: int
    validation_passed: bool
    validation_errors: List[str]
    validation_suggestions: List[str]

    tokens_in: int
    tokens_out: int
    latency_ms: float
    model: str

    limits: Dict[str, Any]
    tool_calls_this_turn: int
```

## Tools

All tools use `@tool` decorators with Pydantic input schemas. The model decides which to call via native function-calling.

| Tool                               | What it does                                            |
| ---------------------------------- | ------------------------------------------------------- |
| `news_search_tool`                 | Search FPL news, injuries, press conferences            |
| `get_expert_tips_tool`             | Scout/pundit consensus from curated expert sources      |
| `get_user_team_info_tool`          | Squad, transfers, budget, captain picks                 |
| `get_user_transfer_history_tool`   | Transfer history for the current season                 |
| `get_user_captain_history_tool`    | Captain pick trends over recent gameweeks               |
| `get_league_standings_tool`        | Mini-league or overall league standings                 |
| `get_players_by_position_tool`     | Transfer candidates filtered by position and max price  |
| `get_player_data_tool`             | Detailed stats, form, and injury news for named players |
| `get_fixtures_for_range_tool`      | Upcoming fixtures with difficulty ratings               |
| `get_player_form_tool`             | Gameweek-by-gameweek form trend for named players       |
| `compare_players_tool`             | Head-to-head stat comparison for up to 5 players        |
| `get_price_movers_tool`            | Players rising/falling in price                         |
| `get_differential_candidates_tool` | Low-ownership players with strong underlying stats      |

## Cost Controls

| Control                       | How it works                                                                                                           |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| **Tool-call budget**          | `MAX_TOOL_CALLS_PER_TURN` (default 6) — tools are unbound from the model once exhausted, forcing a content-only answer |
| **Validation skip**           | No-tool turns skip the validation LLM call entirely (nothing to hallucinate from)                                      |
| **Turn-scoped validation**    | Validation context is this turn's exchange only, not the full conversation                                             |
| **Turn compaction**           | `compact_turn_node` prunes ToolMessages and intermediate AI tool-call messages after each turn                         |
| **Token-based summarization** | `MAX_CONTEXT_TOKENS_BEFORE_SUMMARY` (default 3000) replaces the old message-count trigger                              |
| **Per-user limits hook**      | `core/limits.py::resolve_limits()` returns global defaults today; designed for future subscription tiers               |

## Example Interactions

**Transfer advice:**

```
User: "I have £1.5m in the bank. Any good midfielders I should look at?"

Gaffer: "Nice budget to work with! Palmer (£6.8m) is looking cracking right
now - 3 goals in last 4 games and Chelsea's fixtures are solid. Saka (£9.0m)
is another shout if you can stretch the budget. Both on penalties too 🎯"
```

**Fixture planning:**

```
User: "What are the fixtures like for the next 3 gameweeks?"

Gaffer: "Right, let's look ahead... GW10-12 is massive for City assets -
Bournemouth (H), Brighton (A), Spurs (H). Haaland differential could be huge.
Villa's got the best run though - all green on the ticker!"
```

**Team review:**

```
User: "How's my team looking?"

Gaffer: "Solid squad mate! Sitting at £102.5m value with £0.5m ITB. Template
sorted with Salah and Haaland. Defence might need a look though - three
players with tough fixtures coming up. Fancy making a move there?"
```

## Project Structure

```
src/fpl_gaffer/
├── core/               # Prompts, limits, settings
├── graph/              # State, nodes, edges, graph topology
├── integrations/       # FastAPI app, WhatsApp webhook, services
├── modules/            # FPL API client, data managers, news search
├── tools/              # @tool-decorated functions (fpl, news, user)
└── utils/              # Chain builders, token estimation, helpers
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Author

**DejusDevspace**

- GitHub: [@DejusDevspace](https://github.com/DejusDevspace)
- LinkedIn: [Ojomideju Adejo](https://linkedin.com/in/deju-adejo)
- Twitter: [@d3ju.ai](https://x.com/adejo_deju)

## Acknowledgments

- [LangGraph](https://github.com/langchain-ai/langgraph) for the agent framework
- [Fantasy Premier League API](https://fantasy.premierleague.com) for FPL data
- The FPL community for inspiration and insights

---

<div align="center">

**⚽ Built with passion for FPL managers ⚽**

If you find this project helpful, please consider giving it a ⭐!

</div>
