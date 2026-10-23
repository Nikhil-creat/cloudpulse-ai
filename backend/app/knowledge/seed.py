"""Seed knowledge base: original security / FinOps runbooks (paraphrased control topics, not vendor text)."""
import asyncio

DOCS = [
 {"source": "runbook-s3", "title": "S3 public access", "text": "Enable account-level and bucket-level block public access. Remove public ACLs and policies granting access to everyone. Verify with an access analyzer and enable default encryption with KMS."},
 {"source": "runbook-s3", "title": "S3 encryption and versioning", "text": "Turn on default server-side encryption with a customer managed KMS key, enable versioning and MFA delete for critical buckets, and require TLS with a bucket policy condition."},
 {"source": "runbook-iam", "title": "IAM least privilege", "text": "Replace wildcard actions and resources with scoped permissions. Rotate access keys older than ninety days, remove unused credentials, and require MFA for console users and the root account."},
 {"source": "runbook-network", "title": "Security group exposure", "text": "Restrict SSH port 22 and RDP port 3389 to trusted CIDR ranges or a bastion with session manager. Remove ingress rules open to 0.0.0.0/0 and enable VPC flow logs."},
 {"source": "runbook-finops", "title": "Idle compute rightsizing", "text": "Instances with average CPU under five percent for fourteen days are idle candidates. Stop or downsize them, schedule non-production environments off hours, and tag owners before action."},
 {"source": "runbook-finops", "title": "Savings plans and commitments", "text": "Cover steady baseline usage with savings plans or committed use discounts, keep burst capacity on demand, and review coverage and utilization monthly."},
 {"source": "runbook-finops", "title": "Orphaned storage cleanup", "text": "Find unattached volumes, old snapshots and unused load balancers. Snapshot once, tag for review, then delete after a grace period to reduce monthly spend."},
 {"source": "runbook-logging", "title": "Audit logging", "text": "Enable multi-region audit trail logging with log file validation, deliver to a locked bucket, and alert on console login without MFA and on root account usage."},
 {"source": "runbook-k8s", "title": "Kubernetes pod hardening", "text": "Run containers as non-root with read-only root filesystems, drop all capabilities, set resource requests and limits, and apply network policies with default deny."},
 {"source": "runbook-k8s", "title": "Kubernetes secrets", "text": "Encrypt secrets at rest with a KMS provider, avoid environment variable secrets where possible, and rotate service account tokens with short lifetimes."},
 {"source": "runbook-incident", "title": "Credential leak response", "text": "On a leaked cloud key, deactivate it immediately, review audit logs for the key, rotate dependent secrets, and open an incident with a blast radius assessment."},
 {"source": "runbook-incident", "title": "Cost spike triage", "text": "For a sudden cost spike, break down spend by service and tag, check for crypto mining signatures such as sustained CPU and outbound traffic, and cap the offending account budget."},
 {"source": "runbook-db", "title": "Database exposure", "text": "Place databases in private subnets, disable public accessibility, enforce encryption in transit and at rest, and enable automated backups with tested restores."},
 {"source": "runbook-terraform", "title": "Safe Terraform changes", "text": "Always run plan first, review replacements and deletions, keep state in a remote locked backend, and require approval when the blast radius exceeds the team threshold."},
]


async def main():
    from app.agents import rag
    print("ingested", await rag.ingest(DOCS))


if __name__ == "__main__":
    asyncio.run(main())
