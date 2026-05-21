# DevOps AI Triage Agent
Description

### AI Product Engineer Demo
AI DevOps triage agent using Claude, tool use, and RAG architecture. Built by Tobi Somuyiwa.
---

## What This Is

A production-pattern AI agent that autonomously triages DevOps incidents using tool use and RAG (Retrieval Augmented Generation). Built to demonstrate the same architectural patterns used at Vistra Corp and directly aligned with the AI & Automation Studio work at Intras Cloud Services.

The agent:
1. **Receives** an incident alert or error message
2. **Assesses** severity and SLA implications
3. **Checks** current system status
4. **Retrieves** relevant runbooks from the knowledge base (RAG pattern)
5. **Searches** past incidents for historical patterns
6. **Generates** a structured ServiceNow ticket with diagnosis and remediation steps
7. **Produces** a complete incident report

---

## Setup

```bash
# 1. Clone / navigate to this directory
cd devops_agent

# 2. Install dependency
pip install anthropic

# 3. Set your Anthropic API key
export ANTHROPIC_API_KEY=your_api_key_here

# 4. Run the agent
python agent.py
```

---

## Demo Scenarios

| # | Scenario | Key Tools Used |
|---|----------|----------------|
| 1 | Kubernetes CrashLoopBackOff — Production | search_runbooks, search_past_incidents, assess_severity, check_system_status, generate_servicenow_ticket |
| 2 | Jenkins Pipeline Broken — CI/CD Blocked | search_runbooks, assess_severity, generate_servicenow_ticket |
| 3 | AWS EC2 High CPU — Data Aggregation | search_past_incidents, assess_severity, check_system_status, generate_servicenow_ticket |
| 4 | Custom incident | All tools as needed |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   DevOps AI Agent                        │
│                                                          │
│  ┌──────────────┐    ┌─────────────────────────────┐   │
│  │ Incident In  │───▶│   Claude (LLM Reasoning)    │   │
│  └──────────────┘    └──────────────┬──────────────┘   │
│                                     │ Tool Calls        │
│              ┌──────────────────────┼──────────────┐   │
│              ▼              ▼       ▼       ▼       ▼   │
│        ┌──────────┐ ┌──────────┐ ┌──────┐ ┌──────┐    │
│        │Runbook   │ │Past      │ │System│ │SNOW  │    │
│        │Search    │ │Incident  │ │Status│ │Ticket│    │
│        │(RAG)     │ │Search    │ │Check │ │Gen   │    │
│        └──────────┘ └──────────┘ └──────┘ └──────┘    │
│              │              │                           │
│        ┌─────▼──────────────▼─────┐                   │
│        │    Knowledge Base         │                   │
│        │  runbooks.json            │                   │
│        │  past_incidents.json      │                   │
│        └──────────────────────────┘                   │
└─────────────────────────────────────────────────────────┘
```

### Production Architecture (AWS)

| Local Component | AWS Production Equivalent |
|----------------|---------------------------|
| `anthropic` Python SDK | AWS Bedrock (Claude via Bedrock API) |
| `runbooks.json` | Amazon S3 + OpenSearch / pgvector |
| `past_incidents.json` | Amazon S3 + OpenSearch |
| `agent.py` | AWS Lambda (serverless execution) |
| ServiceNow ticket generation | ServiceNow API integration via Lambda |
| Manual trigger | EventBridge rule (CloudWatch alarm → Lambda) |

---

## Key Technical Concepts Demonstrated

### Tool Use (Agentic AI)
The agent autonomously decides which tools to call, in what order, and how to synthesize the results — without being explicitly told the sequence. This is agentic AI: goal-directed, multi-step reasoning with tool execution.

### RAG (Retrieval Augmented Generation)
The `search_runbooks` and `search_past_incidents` tools implement the RAG pattern — retrieving domain-specific knowledge at query time rather than relying on the LLM's training data alone. In production, this would use vector embeddings and semantic search instead of keyword matching.

### Structured Output
The `generate_servicenow_ticket` tool produces structured, production-ready output that integrates directly with ITSM workflows — demonstrating AI that doesn't just answer questions but takes actions.

### Observability
Every tool call is logged with inputs and outputs — the same auditability pattern required for AI governance in regulated industries (SOC 2, HIPAA, etc.).

---

## Files

```
devops_agent/
├── agent.py                          # Main agent with tool definitions and loop
├── README.md                         # This file
└── knowledge_base/
    ├── runbooks.json                 # 6 operational runbooks (K8s, Jenkins, AWS, Terraform)
    └── past_incidents.json           # 5 historical incident records
```

---

*Built by Tobi Somuyiwa — demonstrating production-pattern AI agent engineering aligned with DevOps and SRE practices.*
