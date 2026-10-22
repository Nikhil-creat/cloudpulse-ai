"""Policy-as-code checks on proposed Terraform before a human ever sees it."""
import re

RULES = [
    ("open-admin-port", "critical", re.compile(r'(from_port|to_port)\s*=\s*(22|3389)[\s\S]{0,200}?0\.0\.0\.0/0|0\.0\.0\.0/0[\s\S]{0,200}?(from_port|to_port)\s*=\s*(22|3389)'),
     "Security group exposes SSH/RDP to the internet"),
    ("wildcard-iam", "critical", re.compile(r'"Action"\s*:\s*"\*"[\s\S]{0,120}"Resource"\s*:\s*"\*"|actions\s*=\s*\["\*"\][\s\S]{0,120}resources\s*=\s*\["\*"\]'),
     "IAM policy grants * on *"),
    ("force-destroy", "high", re.compile(r'force_destroy\s*=\s*true'), "force_destroy enabled"),
    ("encryption-off", "high", re.compile(r'(encrypted|storage_encrypted|kms_encrypted)\s*=\s*false'), "Encryption disabled"),
    ("public-db", "high", re.compile(r'publicly_accessible\s*=\s*true'), "Database is publicly accessible"),
    ("public-bucket", "high", re.compile(r'acl\s*=\s*"public-read(-write)?"|block_public_(acls|policy)\s*=\s*false'), "Bucket is public"),
    ("prod-delete", "high", re.compile(r'(?i)(env|environment)\s*=\s*"prod(uction)?"[\s\S]{0,300}lifecycle\s*{[\s\S]{0,80}prevent_destroy\s*=\s*false'),
     "Prod resource lifecycle protection removed"),
]


def check(hcl: str) -> list[dict]:
    return [{"rule": r, "severity": s, "message": m} for r, s, rx, m in RULES if rx.search(hcl or "")]
