"""
Prompt templates cho AI Recommender.

2 strategies phục vụ thực nghiệm so sánh:
  1. basic:            Prompt đơn giản, không có context bổ sung
  2. context_enriched: Có CIS Benchmark + K8s security docs context

Cả 2 đều dùng cùng model (Gemini 2.5 Flash) và structured output.
Mục tiêu: Đánh giá impact của context quality lên recommendation accuracy.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Reference context excerpts — dùng trong context_enriched prompt
# CIS Kubernetes Benchmark v1.8 + NSA Hardening Guide + K8s Security Docs
# ---------------------------------------------------------------------------

CIS_BENCHMARK_CONTEXT = """
## CIS Kubernetes Benchmark v1.8 — Key Controls

### Section 5.2 — Pod Security Standards
- 5.2.4: Minimize the admission of containers with added capability (HIGH)
  → Container should drop all capabilities: securityContext.capabilities.drop: [ALL]
- 5.2.5: Minimize the admission of containers with allowPrivilegeEscalation (HIGH)
  → Set allowPrivilegeEscalation: false to prevent setuid/setgid exploitation
- 5.2.6: Minimize the admission of root containers (HIGH)
  → Set runAsNonRoot: true and runAsUser: 1000 (non-zero UID)
- 5.2.7: Minimize the admission of containers with the NET_RAW capability (MEDIUM)
  → Drop ALL, add back only NET_BIND_SERVICE if truly needed
- 5.2.11: Ensure resource limits are set (MEDIUM)
  → resources.limits.cpu and resources.limits.memory must be defined

### Section 5.3 — Network Policies
- 5.3.2: Ensure all namespaces have network policies defined (MEDIUM)
  → Default-deny policy + explicit allow rules for required traffic

### Section 5.4 — Secrets Management
- 5.4.1: Prefer using secrets as files over environment variables (MEDIUM)
  → Mount secrets as volumes, not env vars to prevent log exposure

### CIS 1.2.1 — API Server: Anonymous Authentication
  → --anonymous-auth=false prevents unauthenticated K8s API access

### CIS 4.2.1 — Kubelet: Anonymous Authentication
  → --anonymous-auth=false on kubelet prevents direct node API access
"""

NSA_CISA_CONTEXT = """
## NSA/CISA Kubernetes Hardening Guide (2022) — Key Points

### Container Hardening (p.20-25)
- Use non-root containers: Processes as root can escape container isolation
- Read-only filesystems: Prevent malware from persisting to disk
- Immutable infrastructure: Never run as root + read-only FS = gold standard
- Drop capabilities: Linux capabilities (like CAP_SYS_ADMIN) enable container escape

### Image Security (p.14-20)
- Pin image versions: :latest is unpredictable, can introduce breaking changes
- CVE patching: CRITICAL/HIGH CVEs must be patched within 7 days (HIGH) / 24h (CRITICAL)
- Use distroless images: Reduce attack surface by removing shell/package manager

### Network Security (p.26-30)
- Default deny: Implement NetworkPolicy with default-deny first
- Zero-trust networking: Only allow explicitly required communication paths
- Service account tokens: Disable auto-mounting unless required
"""

K8S_SECURITY_DOCS = """
## Kubernetes Security Documentation — Key References

### Pod Security Admission (PSA) Standards
- Privileged: No restrictions (for system pods only)
- Baseline: Prevents known privilege escalation (runAsNonRoot recommended)
- Restricted: Hardened policy (drop ALL, readOnlyRootFilesystem, runAsNonRoot required)

### SecurityContext Fields
- runAsNonRoot: true → Kubernetes validates UID != 0 before starting container
- runAsUser: <uid> → Numeric UID (>0) for container process
- readOnlyRootFilesystem: true → Container can't write to / filesystem
- allowPrivilegeEscalation: false → Prevents setuid/setgid execution
- capabilities.drop: [ALL] → Removes all POSIX capabilities from container

### Resource Quotas
- Without limits: OOMKilled events, CPU throttling, noisy neighbor problems
- Recommended pattern: requests = 1/4 of limits for autoscaling headroom
"""

# ---------------------------------------------------------------------------
# Prompt Templates
# ---------------------------------------------------------------------------

BASIC_PROMPT_TEMPLATE = """\
You are a Kubernetes security engineer. Analyze this compliance violation and provide a fix.

## Violation Details
- Finding ID: {finding_id}
- Resource: {resource_kind}/{resource_name} in namespace '{namespace}'
- Policy/Check: {title}
- Severity: {severity}
- Source: {source}
- Description: {description}

## Task
Provide a specific, actionable fix for this violation.

Respond with valid JSON exactly matching this schema:
{response_schema}
"""

CONTEXT_ENRICHED_PROMPT_TEMPLATE = """\
You are a Kubernetes security expert specializing in CIS Benchmarks, NSA/CISA hardening, \
and production Kubernetes security. Analyze this compliance violation using the provided \
reference context to give a comprehensive, accurate fix.

## Violation Details
- Finding ID: {finding_id}
- Resource: {resource_kind}/{resource_name} in namespace '{namespace}'
- Policy/Check: {title}
- Severity: {severity}
- Source: {source}
- Description: {description}

---

## Reference Context

### CIS Kubernetes Benchmark v1.8
{cis_benchmark_excerpt}

### NSA/CISA Kubernetes Hardening Guide
{nsa_cisa_excerpt}

### Kubernetes Security Documentation
{k8s_security_docs}

---

## Instructions
1. Identify the exact root cause of this violation and its security impact
2. Provide a drop-in YAML patch that resolves the violation (copy-paste ready)
3. List the specific CIS Benchmark control numbers this violation affects
4. Assess urgency based on exploitability and impact

Respond with valid JSON exactly matching this schema:
{response_schema}
"""


def build_basic_prompt(
    finding_id: str,
    resource_kind: str,
    resource_name: str,
    namespace: str,
    title: str,
    severity: str,
    source: str,
    description: str,
    response_schema: str,
) -> str:
    """Build basic prompt — no extra context."""
    return BASIC_PROMPT_TEMPLATE.format(
        finding_id=finding_id,
        resource_kind=resource_kind,
        resource_name=resource_name,
        namespace=namespace or "cluster-wide",
        title=title,
        severity=severity,
        source=source,
        description=description,
        response_schema=response_schema,
    )


def build_context_enriched_prompt(
    finding_id: str,
    resource_kind: str,
    resource_name: str,
    namespace: str,
    title: str,
    severity: str,
    source: str,
    description: str,
    response_schema: str,
) -> str:
    """Build context-enriched prompt với CIS Benchmark + K8s security context."""
    return CONTEXT_ENRICHED_PROMPT_TEMPLATE.format(
        finding_id=finding_id,
        resource_kind=resource_kind,
        resource_name=resource_name,
        namespace=namespace or "cluster-wide",
        title=title,
        severity=severity,
        source=source,
        description=description,
        cis_benchmark_excerpt=CIS_BENCHMARK_CONTEXT,
        nsa_cisa_excerpt=NSA_CISA_CONTEXT,
        k8s_security_docs=K8S_SECURITY_DOCS,
        response_schema=response_schema,
    )


# ---------------------------------------------------------------------------
# Part 2: AI Summary Prompt Templates
# ---------------------------------------------------------------------------

EXECUTIVE_SUMMARY_PROMPT = """\
You are a Kubernetes security expert reviewing a compliance scan report for a production cluster.

## Scan Results
- Overall Score: {overall_score}/100 ({classification})
- Domain Scores:
{domain_scores}
- Total Findings: {total_findings} (Critical: {critical}, High: {high}, Medium: {medium}, Low: {low})

## Top Findings Summary
{findings_summary}

Provide a security executive summary as a JSON response with:
1. overall_assessment: Security posture analysis (2-3 sentences, actionable)
2. risk_level: "critical" | "high" | "moderate" | "low"
3. top_priorities: Top 3 fixes (max 3 items) each with finding_id, title, severity, fix_summary (1-line), estimated_effort
4. remediation_phases: Three phases — immediate (CRITICAL, fix today), this_sprint (HIGH, fix this week), backlog (MEDIUM/LOW, schedule)
   Each phase: phase, description, finding_ids, total_estimated_effort
5. trend_prediction: "improving" | "stable" | "declining"

Response schema:
{response_schema}
"""

REMEDIATION_PLAN_PROMPT = """\
You are a Kubernetes security expert creating a prioritized remediation plan for a Kubernetes cluster.

## Violations to Fix
{violations_detail}

Create a prioritized remediation plan. Organize by urgency:
- Phase 1 (immediate): CRITICAL severity — fix today, actively exploitable
- Phase 2 (this_sprint): HIGH severity — fix this sprint, exploit likely
- Phase 3 (backlog): MEDIUM/LOW severity — schedule improvement

For each phase provide:
- phase: "immediate" | "this_sprint" | "backlog"
- description: brief phase description
- finding_ids: list of finding IDs in this phase
- total_estimated_effort: aggregated effort estimate for the phase

Response schema:
{response_schema}
"""


def build_executive_summary_prompt(
    overall_score: float,
    classification: str,
    domain_scores: str,
    total_findings: int,
    critical: int,
    high: int,
    medium: int,
    low: int,
    findings_summary: str,
    response_schema: str,
) -> str:
    """Build executive summary prompt."""
    return EXECUTIVE_SUMMARY_PROMPT.format(
        overall_score=round(overall_score, 1),
        classification=classification,
        domain_scores=domain_scores,
        total_findings=total_findings,
        critical=critical,
        high=high,
        medium=medium,
        low=low,
        findings_summary=findings_summary,
        response_schema=response_schema,
    )


def build_remediation_plan_prompt(
    violations_detail: str,
    response_schema: str,
) -> str:
    """Build remediation plan prompt."""
    return REMEDIATION_PLAN_PROMPT.format(
        violations_detail=violations_detail,
        response_schema=response_schema,
    )

