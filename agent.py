"""
DevOps AI Agent — Tool Use + RAG
Tobi Somuyiwa | AI Product Engineer Demo

This agent simulates what was built at Vistra Corp:
- Ingests an alert or incident description
- Retrieves relevant runbooks and past incidents (RAG pattern)
- Uses tool calls to diagnose, assess severity, and recommend remediation
- Produces a structured incident report

Production architecture would replace local JSON with:
- AWS Bedrock (LLM layer)
- Amazon OpenSearch / pgvector (vector store)
- AWS Lambda (serverless agent execution)
- S3 (runbook/incident storage)
- ServiceNow API (ticket creation)
"""

import json
import os
import re
from datetime import datetime
from anthropic import Anthropic

client = Anthropic()

# ── Load Knowledge Base ────────────────────────────────────────────────────────

def load_knowledge_base():
    base_path = os.path.join(os.path.dirname(__file__), "knowledge_base")
    with open(f"{base_path}/runbooks.json") as f:
        runbooks = json.load(f)
    with open(f"{base_path}/past_incidents.json") as f:
        past_incidents = json.load(f)
    return runbooks, past_incidents

RUNBOOKS, PAST_INCIDENTS = load_knowledge_base()

# ── Tool Definitions ───────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "search_runbooks",
        "description": "Search the knowledge base for runbooks relevant to the incident. Returns matching runbooks with resolution steps.",
        "input_schema": {
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Keywords to search for in runbooks (e.g. ['kubernetes', 'crashloopbackoff', 'pod'])"
                }
            },
            "required": ["keywords"]
        }
    },
    {
        "name": "search_past_incidents",
        "description": "Search past incident records for similar issues and their resolutions. Useful for pattern matching and historical context.",
        "input_schema": {
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Keywords to match against past incident titles, symptoms, and tags"
                }
            },
            "required": ["keywords"]
        }
    },
    {
        "name": "assess_severity",
        "description": "Assess the severity level of an incident based on its impact and affected systems.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symptoms": {"type": "string", "description": "Description of the incident symptoms"},
                "affected_system": {"type": "string", "description": "The system or service affected"},
                "environment": {"type": "string", "description": "The environment affected (production, staging, dev)"}
            },
            "required": ["symptoms", "affected_system", "environment"]
        }
    },
    {
        "name": "generate_servicenow_ticket",
        "description": "Generate a formatted ServiceNow incident ticket with all required fields populated.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Incident title"},
                "severity": {"type": "string", "description": "Severity level: CRITICAL, HIGH, MEDIUM, LOW"},
                "affected_system": {"type": "string", "description": "System or service affected"},
                "description": {"type": "string", "description": "Full incident description"},
                "initial_diagnosis": {"type": "string", "description": "Initial root cause hypothesis"},
                "recommended_actions": {"type": "array", "items": {"type": "string"}, "description": "List of recommended remediation steps"}
            },
            "required": ["title", "severity", "affected_system", "description", "initial_diagnosis", "recommended_actions"]
        }
    },
    {
        "name": "check_system_status",
        "description": "Check the simulated status of infrastructure components (AWS services, Kubernetes clusters, CI/CD systems).",
        "input_schema": {
            "type": "object",
            "properties": {
                "system": {"type": "string", "description": "The system to check status for (e.g. 'kubernetes-cluster', 'jenkins', 'aws-ec2', 'terraform')"}
            },
            "required": ["system"]
        }
    }
]

# ── Tool Execution ─────────────────────────────────────────────────────────────

def search_runbooks(keywords):
    keywords_lower = [k.lower() for k in keywords]
    matches = []
    for rb in RUNBOOKS:
        score = 0
        searchable = (rb["title"] + " " + rb["category"] + " " +
                     " ".join(rb["symptoms"]) + " " + " ".join(rb["root_causes"])).lower()
        for kw in keywords_lower:
            if kw in searchable:
                score += 1
        if score > 0:
            matches.append({"score": score, "runbook": rb})
    matches.sort(key=lambda x: x["score"], reverse=True)
    top = matches[:2]
    if not top:
        return {"found": False, "message": "No matching runbooks found for the given keywords."}
    return {
        "found": True,
        "count": len(top),
        "runbooks": [m["runbook"] for m in top]
    }

def search_past_incidents(keywords):
    keywords_lower = [k.lower() for k in keywords]
    matches = []
    for inc in PAST_INCIDENTS:
        score = 0
        searchable = (inc["title"] + " " + inc["symptoms"] + " " +
                     inc["root_cause"] + " " + " ".join(inc["tags"])).lower()
        for kw in keywords_lower:
            if kw in searchable:
                score += 1
        if score > 0:
            matches.append({"score": score, "incident": inc})
    matches.sort(key=lambda x: x["score"], reverse=True)
    top = matches[:2]
    if not top:
        return {"found": False, "message": "No similar past incidents found."}
    return {
        "found": True,
        "count": len(top),
        "incidents": [m["incident"] for m in top]
    }

def assess_severity(symptoms, affected_system, environment):
    severity_map = {
        "production": "HIGH",
        "prod": "HIGH",
    }
    critical_keywords = ["down", "unreachable", "not responding", "outage", "crash", "oom", "killed"]
    high_keywords = ["degraded", "slow", "spike", "failure", "failed", "error", "loop"]

    env_base = severity_map.get(environment.lower(), "MEDIUM")
    combined = (symptoms + " " + affected_system).lower()

    if any(kw in combined for kw in critical_keywords) and environment.lower() in ["production", "prod"]:
        severity = "CRITICAL"
        p1 = True
    elif any(kw in combined for kw in critical_keywords):
        severity = "HIGH"
        p1 = False
    elif any(kw in combined for kw in high_keywords) and environment.lower() in ["production", "prod"]:
        severity = "HIGH"
        p1 = False
    else:
        severity = env_base
        p1 = False

    return {
        "severity": severity,
        "p1_incident": p1,
        "sla_response_time": "15 minutes" if p1 else ("30 minutes" if severity == "HIGH" else "2 hours"),
        "escalation_required": p1,
        "rationale": f"{'Production environment + ' if environment.lower() in ['production','prod'] else ''}symptoms indicate {severity.lower()} impact"
    }

def generate_servicenow_ticket(title, severity, affected_system, description, initial_diagnosis, recommended_actions):
    ticket_id = f"INC{datetime.now().strftime('%Y%m%d%H%M')}"
    return {
        "ticket_id": ticket_id,
        "status": "GENERATED",
        "ticket": {
            "Number": ticket_id,
            "Title": title,
            "Severity": severity,
            "Priority": {"CRITICAL": "P1", "HIGH": "P2", "MEDIUM": "P3", "LOW": "P4"}.get(severity, "P3"),
            "Affected_Service": affected_system,
            "Reported_At": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
            "Assigned_Team": "DevOps Engineering",
            "Description": description,
            "Initial_Diagnosis": initial_diagnosis,
            "Recommended_Actions": recommended_actions,
            "Status": "Open",
            "Source": "AI Triage Agent"
        }
    }

def check_system_status(system):
    status_db = {
        "kubernetes-cluster": {"status": "DEGRADED", "details": "2 nodes reporting high memory pressure. 4 pods in CrashLoopBackOff state in namespace prod-energy.", "last_checked": "Just now"},
        "jenkins": {"status": "OPERATIONAL", "details": "All build agents responsive. Last successful build: 12 minutes ago.", "last_checked": "Just now"},
        "aws-ec2": {"status": "WARNING", "details": "3 instances showing CPU > 80%. Auto-scaling group triggered. 2 new instances launching.", "last_checked": "Just now"},
        "terraform": {"status": "OPERATIONAL", "details": "No active state locks. Last apply: 2 hours ago in staging environment.", "last_checked": "Just now"},
        "prometheus": {"status": "OPERATIONAL", "details": "All targets scraping. 2 active alerts firing: HighCPU (warning), PodRestartRate (critical).", "last_checked": "Just now"},
        "nexus": {"status": "OPERATIONAL", "details": "Artifact repository healthy. Storage at 43% capacity.", "last_checked": "Just now"},
    }
    key = system.lower().replace(" ", "-")
    for k, v in status_db.items():
        if k in key or key in k:
            return {"system": system, **v}
    return {"system": system, "status": "UNKNOWN", "details": "System not found in monitoring registry.", "last_checked": "Just now"}

def execute_tool(tool_name, tool_input):
    if tool_name == "search_runbooks":
        return search_runbooks(tool_input["keywords"])
    elif tool_name == "search_past_incidents":
        return search_past_incidents(tool_input["keywords"])
    elif tool_name == "assess_severity":
        return assess_severity(tool_input["symptoms"], tool_input["affected_system"], tool_input["environment"])
    elif tool_name == "generate_servicenow_ticket":
        return generate_servicenow_ticket(
            tool_input["title"], tool_input["severity"], tool_input["affected_system"],
            tool_input["description"], tool_input["initial_diagnosis"], tool_input["recommended_actions"]
        )
    elif tool_name == "check_system_status":
        return check_system_status(tool_input["system"])
    else:
        return {"error": f"Unknown tool: {tool_name}"}

# ── Agent Loop ─────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert DevOps AI Agent specializing in incident triage, root cause analysis, and remediation for cloud infrastructure environments.

You have access to tools that allow you to:
1. Search runbooks for relevant resolution procedures
2. Search past incidents for historical patterns
3. Assess incident severity based on symptoms and environment
4. Check current system status
5. Generate structured ServiceNow incident tickets

When given an incident alert or description, you will:
1. Assess the severity and urgency first
2. Check the status of relevant systems
3. Search for relevant runbooks and past similar incidents
4. Synthesize findings into a clear diagnosis with probable root causes
5. Generate a ServiceNow ticket with all findings and recommended actions
6. Provide a clear, concise incident report

Always be systematic, thorough, and prioritize production environments. Think like a senior SRE — not just what's wrong, but why it's wrong and how to prevent recurrence.

Your final output should always be a well-structured incident report."""

def run_agent(incident_description):
    print("\n" + "="*65)
    print("  DevOps AI Agent — Incident Triage System")
    print("  Built on: Claude + Tool Use + RAG Knowledge Base")
    print("="*65)
    print(f"\n📨 INCOMING ALERT:\n{incident_description}\n")
    print("-"*65)

    messages = [{"role": "user", "content": incident_description}]
    tool_call_count = 0

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages
        )

        # Process response content
        tool_uses = []
        text_blocks = []

        for block in response.content:
            if block.type == "tool_use":
                tool_uses.append(block)
            elif block.type == "text" and block.text.strip():
                text_blocks.append(block.text)

        # Print any text output
        for text in text_blocks:
            if response.stop_reason != "tool_use":
                print(f"\n{text}")

        # If no tool calls, we're done
        if response.stop_reason == "end_turn" or not tool_uses:
            if text_blocks:
                print("\n" + "="*65)
                print("  AGENT COMPLETE")
                print("="*65)
            break

        # Execute all tool calls
        tool_results = []
        for tool_use in tool_uses:
            tool_call_count += 1
            print(f"\n🔧 Tool Call #{tool_call_count}: {tool_use.name}")
            print(f"   Input: {json.dumps(tool_use.input, indent=2)}")

            result = execute_tool(tool_use.name, tool_use.input)

            # Print condensed result
            if tool_use.name == "search_runbooks" and result.get("found"):
                print(f"   ✓ Found {result['count']} matching runbook(s): {[r['title'] for r in result['runbooks']]}")
            elif tool_use.name == "search_past_incidents" and result.get("found"):
                print(f"   ✓ Found {result['count']} similar incident(s): {[i['id'] for i in result['incidents']]}")
            elif tool_use.name == "assess_severity":
                print(f"   ✓ Severity: {result['severity']} | P1: {result['p1_incident']} | SLA: {result['sla_response_time']}")
            elif tool_use.name == "check_system_status":
                print(f"   ✓ {result['system']}: {result['status']} — {result['details'][:60]}...")
            elif tool_use.name == "generate_servicenow_ticket":
                print(f"   ✓ Ticket {result['ticket_id']} generated | Priority: {result['ticket']['Priority']}")
            else:
                print(f"   ✓ Result: {str(result)[:100]}")

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": json.dumps(result)
            })

        # Add assistant response and tool results to messages
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    print(f"\n[Agent completed with {tool_call_count} tool calls]\n")
    return response

# ── Demo Scenarios ─────────────────────────────────────────────────────────────

DEMO_SCENARIOS = {
    "1": {
        "name": "Kubernetes CrashLoopBackOff — Production",
        "alert": """
ALERT: PodRestartRate CRITICAL
Environment: Production
Namespace: prod-energy
Service: energy-reporting-service
Message: Pod energy-reporting-service-7d9f8b-xk2p9 has restarted 8 times in the last 10 minutes.
Status: CrashLoopBackOff
Last Error: OOMKilled
Timestamp: 2025-05-19 09:42:11 UTC
"""
    },
    "2": {
        "name": "Jenkins Pipeline Broken — CI/CD Blocked",
        "alert": """
ALERT: Jenkins Build Failure
Environment: CI/CD
Job: fossil-data-pipeline/main
Stage: Publish Artifacts
Error: Failed to deploy artifacts to Nexus repository. Connection refused on port 8081.
Build #247 FAILED
All deployments to staging blocked.
Timestamp: 2025-05-19 10:15:33 UTC
"""
    },
    "3": {
        "name": "AWS EC2 High CPU — Data Aggregation Service",
        "alert": """
ALERT: HighCPUUtilization WARNING → CRITICAL
Environment: Production
Instance: i-0a3b2c1d4e5f (m5.xlarge)
Service: fossil-data-aggregation
CPU Utilization: 96% (threshold: 85%)
Duration: 18 minutes sustained
Impact: API response times degraded to 8-12 seconds (SLA: < 2 seconds)
Timestamp: 2025-05-19 11:03:45 UTC
"""
    }
}

def main():
    print("\n" + "="*65)
    print("  DevOps AI Triage Agent")
    print("  Tobi Somuyiwa | AI Product Engineer Demo")
    print("="*65)
    print("\nSelect a demo scenario or enter your own incident:")
    for key, scenario in DEMO_SCENARIOS.items():
        print(f"  {key}. {scenario['name']}")
    print("  4. Enter custom incident")
    print()

    choice = input("Choice (1-4): ").strip()

    if choice in DEMO_SCENARIOS:
        incident = DEMO_SCENARIOS[choice]["alert"]
    elif choice == "4":
        print("\nPaste your incident alert (press Enter twice when done):")
        lines = []
        while True:
            line = input()
            if line == "" and lines and lines[-1] == "":
                break
            lines.append(line)
        incident = "\n".join(lines)
    else:
        print("Invalid choice. Running scenario 1.")
        incident = DEMO_SCENARIOS["1"]["alert"]

    run_agent(incident)

if __name__ == "__main__":
    main()
