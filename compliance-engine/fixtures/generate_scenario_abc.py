"""
Sinh bộ fixture `scenario-abc/` mô phỏng workload A (poor), B (excellent), C (fair)
trong namespace `compliance-test`, khớp với idp-gitops/experiments/.

Chạy lại sau khi sửa kỳ vọng:  python fixtures/generate_scenario_abc.py
Dữ liệu là MÔ PHỎNG cho smoke test, không phải kết quả đo trên cluster.
"""

from __future__ import annotations

import json
from pathlib import Path

NS = "compliance-test"
OUT = Path(__file__).parent / "scenario-abc"

# policy -> (rule, severity) khớp 8 ClusterPolicy trong idp-gitops/platform/kyverno/policies
POLICIES = {
    "disallow-privilege-escalation": ("autogen-deny-privilege-escalation", "high"),
    "require-run-as-non-root": ("autogen-run-as-non-root", "high"),
    "require-read-only-rootfs": ("autogen-read-only-rootfs", "medium"),
    "drop-all-capabilities": ("autogen-drop-capabilities", "high"),
    "disallow-latest-tag": ("autogen-validate-image-tag", "high"),
    "require-resource-limits": ("autogen-resource-limits-required", "medium"),
    "require-labels": ("app-labels-required", "low"),
    "require-probes": ("probes-required", "medium"),
}

# Kết quả kỳ vọng theo comment trong manifest của từng workload
EXPECTED = {
    "workload-a-poor": {p: "fail" for p in POLICIES},
    "workload-b-excellent": {p: "pass" for p in POLICIES},
    "workload-c-fair": {
        "disallow-privilege-escalation": "pass",
        "require-run-as-non-root": "pass",
        "require-read-only-rootfs": "fail",
        "drop-all-capabilities": "fail",
        "disallow-latest-tag": "pass",
        "require-resource-limits": "pass",
        "require-labels": "fail",
        "require-probes": "pass",
    },
}

IMAGES = {
    "workload-a-poor": ("library/nginx", "latest"),
    "workload-b-excellent": ("nginxinc/nginx-unprivileged", "1.27.0"),
    "workload-c-fair": ("nginxinc/nginx-unprivileged", "1.24.0"),
}

VULNS = {
    "workload-a-poor": [
        ("CVE-2024-0001", "libssl3", "3.0.11-1", "3.0.13-1", "HIGH"),
        ("CVE-2024-0002", "zlib1g", "1.2.13", "1.3.1", "MEDIUM"),
    ],
    "workload-b-excellent": [],
    "workload-c-fair": [
        ("CVE-2023-44487", "nginx", "1.24.0", "1.25.3", "HIGH"),
        ("CVE-2024-0003", "libexpat1", "2.5.0-1", "2.5.0-1+deb12u1", "CRITICAL"),
        ("CVE-2024-0004", "libssl3", "3.0.11-1", "3.0.13-1", "HIGH"),
    ],
}


def policy_reports() -> dict:
    items = []
    for name, results in EXPECTED.items():
        scope = {"apiVersion": "apps/v1", "kind": "Deployment", "name": name, "namespace": NS}
        items.append(
            {
                "apiVersion": "wgpolicyk8s.io/v1alpha2",
                "kind": "PolicyReport",
                "metadata": {"name": f"fixture-{name}", "namespace": NS},
                "scope": scope,
                "summary": {
                    "pass": sum(r == "pass" for r in results.values()),
                    "fail": sum(r == "fail" for r in results.values()),
                },
                "results": [
                    {
                        "policy": policy,
                        "rule": POLICIES[policy][0],
                        "result": result,
                        "severity": POLICIES[policy][1],
                        "message": f"fixture: {policy} {result} on {name}",
                        "resources": [scope],
                    }
                    for policy, result in results.items()
                ],
            }
        )
    return {"apiVersion": "v1", "kind": "List", "items": items}


def vulnerability_reports() -> dict:
    items = []
    for name, vulns in VULNS.items():
        repo, tag = IMAGES[name]
        items.append(
            {
                "apiVersion": "aquasecurity.github.io/v1alpha1",
                "kind": "VulnerabilityReport",
                "metadata": {
                    "name": f"replicaset-{name}-fixture-app",
                    "namespace": NS,
                    "labels": {
                        "trivy-operator.resource.kind": "ReplicaSet",
                        "trivy-operator.resource.name": f"{name}-fixture",
                        "trivy-operator.resource.namespace": NS,
                        "trivy-operator.container.name": "app",
                    },
                },
                "report": {
                    "artifact": {"repository": repo, "tag": tag},
                    "summary": {
                        "criticalCount": sum(v[4] == "CRITICAL" for v in vulns),
                        "highCount": sum(v[4] == "HIGH" for v in vulns),
                    },
                    "vulnerabilities": [
                        {
                            "vulnerabilityID": cve,
                            "resource": pkg,
                            "installedVersion": installed,
                            "fixedVersion": fixed,
                            "severity": sev,
                            "title": f"fixture {cve} in {pkg}",
                        }
                        for cve, pkg, installed, fixed, sev in vulns
                    ],
                },
            }
        )
    return {"apiVersion": "v1", "kind": "List", "items": items}


def kubebench() -> dict:
    # EKS benchmark: section 3 = Worker Node (kubelet). Mô phỏng 1 node.
    results = [
        ("3.1.1", "Ensure kubeconfig file permissions are 644 or more restrictive", "PASS"),
        ("3.2.1", "Ensure that the Anonymous Auth is Not Enabled", "PASS"),
        ("3.2.2", "Ensure that the --authorization-mode argument is not set to AlwaysAllow", "PASS"),
        ("3.2.4", "Ensure that the --read-only-port is disabled", "FAIL"),
        ("3.2.9", "Ensure that the --event-qps argument is set to 0 or a level which ensures appropriate event capture", "WARN"),
    ]
    return {
        "Controls": [
            {
                "id": "3",
                "version": "eks-1.2.0",
                "text": "Worker Node Security Configuration",
                "node_type": "node",
                "tests": [
                    {
                        "section": "3.x",
                        "desc": "fixture",
                        "results": [
                            {
                                "test_number": num,
                                "test_desc": desc,
                                "status": status,
                                "remediation": "fixture remediation",
                                "scored": True,
                            }
                            for num, desc, status in results
                        ],
                    }
                ],
            }
        ]
    }


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for fname, data in {
        "policyreports.json": policy_reports(),
        "vulnerabilityreports.json": vulnerability_reports(),
        "kubebench.json": kubebench(),
    }.items():
        (OUT / fname).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {OUT / fname}")


if __name__ == "__main__":
    main()
