# Jess Architecture

## Two Implementations

There are two separate Jess implementations:

### 1. Internal Jess (`agents/jess_agent.py` in main app)

**Location:** `/Users/andyseaman/Notebooks/claude_agent_master/claude_agent_new_v11/agents/jess_agent.py`

**Purpose:** Full-featured video intelligence for the Minerva app

**Characteristics:**
- Direct access to Minerva-MCP search index
- Hardcoded video catalog with metadata
- Anthropic API calls for synthesis
- BaseAgent integration (status logging, message manager)
- ~600 lines of code

**Data flow:**
```
User Query → Internal Jess → Minerva-MCP (direct) → Response
```

### 2. Client Jess (`minerva-jess` package)

**Location:** This repository (`/Users/andyseaman/Notebooks/minerva-jess`)

**Purpose:** SDK delivered to client for their integrations

**Characteristics:**
- Thin client - delegates everything to Orca gateway
- No direct Minerva access (architecture hidden)
- Configurable name/icon via config.yaml
- Standalone (no BaseAgent dependency)
- ~280 lines of code

**Data flow:**
```
User Query → Client Jess → Orca Gateway → Minerva-MCP → Response
```

## Key Differences

| Aspect | Internal Jess | Client Jess |
|--------|--------------|-------------|
| Search logic | Local (FTS5 + embeddings) | Via Orca |
| Synthesis | Direct Anthropic API | Via Orca |
| Video catalog | Hardcoded | From Orca |
| Framework | BaseAgent integration | Standalone |
| Customizable | No | Yes (config.yaml) |

## Change Isolation

**Changes are isolated between implementations:**

- Client modifies `minerva-jess` → No effect on internal app
- You modify internal Jess → No effect on client's SDK
- You modify Minerva/Orca backend → Both benefit

**This is by design:**
- Client can't break your app
- Client can't reverse-engineer your implementation
- Backend improvements benefit everyone

## Future Considerations

If renaming to avoid confusion:
- Internal: Rename to "Jed" (`jed_agent.py`)
- Client: Keep as "Jess" (their branded agent)

## Updating Client

If client needs new features:
1. Implement in Minerva/Orca backend (they get it automatically)
2. Or update `minerva-jess` package and notify client to pull

Client changes to their copy do NOT sync back automatically.
You won't know about their changes unless they tell you.
