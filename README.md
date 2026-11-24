# tenant-forge-cli

**Customer tenant onboarding in one command: validated inputs, generated Terraform variables, and a security-baselined AWS environment per tenant.**

TenantForge is a Field Engineering tool: it packages the repeatable part of customer onboarding (VPC, private subnet, encrypted ingest-logs bucket, consistent tagging) into a CLI plus a Terraform module, so every tenant gets the same auditable baseline instead of a hand-built snowflake.

---

## The business problem

Field engineers onboard customer tenants the same way every time, but usually by hand: copy an old `terraform apply`, find-replace tenant names, hope the CIDR math is right, and remember (or forget) the tagging and encryption steps. That is slow, error-prone, and impossible to audit. TenantForge fixes the three failure points:

1. **Input discipline.** Tenant IDs and CIDR blocks are validated twice (Python at generation time, Terraform variable validation at plan time), so `acme_corp!` and `/8` mega-blocks never reach infrastructure.
2. **One baseline.** Every tenant environment is materialized from one reviewed Terraform module with enforced tags (`Tenant`, `Environment`, `ManagedBy = "TenantForge-Terraform"`).
3. **Repeatable handoff.** Dry run by default, explicit `--apply` for changes, generated variable files, and a documented Day-2 destroy path.

## Architecture

```
                         +------------------------------------------------------+
                         |                      AWS Cloud                       |
                         |                                                      |
  Field Engineer         |  +------------------------------------------------+  |
  ----------------       |  |  Tenant VPC (10.20.0.0/16)                     |  |
  tenant-forge CLI   --->|  |  Tags: Tenant, Environment,                    |  |
  1. validates inputs    |  |        ManagedBy = TenantForge-Terraform       |  |
  2. writes tfvars       |  |                                                |  |
  3. runs terraform      |  |  +------------------------------------------+  |  |
                         |  |  | Private subnet: cidrsubnet(vpc, 4, 1)    |  |  |
                         |  |  | = 10.20.16.0/20 for a /16 VPC            |  |  |
                         |  |  | no public IPs, DNS hostnames + support   |  |  |
                         |  |  +------------------------------------------+  |  |
                         |  +------------------------------------------------+  |
                         |                                                      |
                         |  S3: <project>-<tenant>-<env>-ingest-logs            |
                         |  - SSE-S3 encryption at rest (AES256)                |
                         |  - all four public access block flags ON             |
                         |  - force_destroy = true (see trade-offs)             |
                         +------------------------------------------------------+
```

For a `/16` VPC, `cidrsubnet(var.vpc_cidr, 4, 1)` yields `10.20.16.0/20`; a `/24` VPC yields a `/28` subnet. Every tenant lives inside its own CIDR, so overlapping tenants are impossible by construction.

## Security guardrails (NIST SP 800-53 aligned defaults)

These are baseline defaults, not a certification claim. They map to the control families a FedRAMP or HIPAA reviewer will ask about:

| Default in this repo | Rationale | SP 800-53 alignment |
|---|---|---|
| Private subnet with `map_public_ip_on_launch = false`, no internet gateway | Tenant workloads launch without routable public exposure | SC-7 (Boundary Protection) |
| S3 server-side encryption with AES256 on every ingest bucket | Data at rest is never unencrypted, with no customer decision required | SC-28 (Protection of Information at Rest) |
| All four `aws_s3_bucket_public_access_block` flags set to `true` | Public exposure of tenant logs is blocked at the account-resource level, not by policy hope | AC-3 / SC-7 |
| Dedicated per-tenant ingest bucket | Tenant log data is isolated per customer, simplifying retention and egress review | AU-9 / SC-2 (tenant isolation) |
| Uniform `Tenant` / `Environment` / `ManagedBy` tags | Every resource is attributable to a tenant for audit and automated guardrails | CM-6 / CM-8 |
| Dual validation of tenant ID and CIDR (Python + Terraform) | Malformed or oversized inputs fail before any API call | CA-2 / SA-8 (assessment of security controls) |
| Dry run (`plan`) as the CLI default | No infrastructure change happens without an explicit `--apply` | CM-5 (change control) |

## Engineering trade-offs

Honest trade-offs, made deliberately for field velocity:

- **Single AZ private subnet.** One subnet keeps the baseline minimal and the bill near zero. Production tenants should add AZs and subnets per tier; the module is structured to grow.
- **No NAT gateway or VPC endpoints.** The private subnet has no egress path at all, which is a feature for isolation and a limitation for workloads that need updates. Add endpoints deliberately, per customer network policy.
- **`force_destroy = true` on the ingest bucket.** Lets a Day-2 `terraform destroy` actually finish instead of orphaning buckets. For tenants with data-retention obligations, flip this to `false` and add versioning before go-live.
- **SSE-S3 (AES256) instead of SSE-KMS.** Zero key management for the baseline. Customers with CMK requirements can swap `sse_algorithm` and add a KMS key resource; the plan diff will make the change visible.
- **Local Terraform state.** CI runs `init -backend=false`; field runs use whatever backend the engagement standardizes on. For anything shared, configure an S3 backend with DynamoDB locking before the second engineer touches the tenant. The generated lock file is committed for provider reproducibility.
- **Bootstrap token preview on stdout.** The CLI prints a fresh `tf_live_...` token for the handoff checklist. It is generated at run time, never persisted by the tool, and must be rotated by the customer; for high-assurance engagements, replace with a secrets-manager write.
- **`boto3` is declared but not yet exercised.** It is pinned now because the next increment (bootstrap token provisioning and SSM parameter write) uses it, keeping the dependency surface stable.

## 5-minute quickstart

```bash
# 1. Clone and install
git clone https://github.com/BLuef0x27/tenant-forge-cli.git
cd tenant-forge-cli
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 2. Offline verification (no AWS credentials needed)
pytest -v
terraform -chdir=terraform fmt -check -recursive
terraform -chdir=terraform init -backend=false
terraform -chdir=terraform validate

# 3. Dry run: validate inputs, write tfvars, preview token
tenant-forge onboard -t acme-corp -e staging --cidr 10.20.0.0/16

# 4. Live apply (requires AWS credentials with VPC + S3 permissions)
tenant-forge onboard -t acme-corp -e staging --cidr 10.20.0.0/16 --apply
```

What each stage proves:

- **Offline verification** catches code defects, formatting drift, and HCL errors with zero cloud risk.
- **Dry run** writes `tenants/acme-corp-staging.tfvars` and previews the bootstrap token, then runs `terraform -chdir=terraform plan -var-file=../tenants/acme-corp-staging.tfvars` so you can read the diff before anything changes.
- **Live apply** runs the same command with `apply -auto-approve`. Use it after the plan review, never on a Friday.

## Day-2 handoff and destroy

Handoff checklist:

1. Rotate the bootstrap API token issued during onboarding (the CLI prints it once; it is never persisted).
2. Record the three outputs (`tenant_vpc_id`, `tenant_private_subnet_id`, `tenant_ingest_bucket_arn`) in the customer runbook.
3. If more than one engineer will touch the tenant, move state to a remote backend (S3 + DynamoDB locking) before proceeding.
4. Re-run `terraform -chdir=terraform plan -var-file=...` after any manual console change; the diff is your drift alarm.

Destroy (full teardown):

```bash
terraform -chdir=terraform destroy -var-file=../tenants/acme-corp-staging.tfvars
```

Because `force_destroy = true`, the ingest bucket and every object in it are deleted. Confirm the customer has no retention obligation first; otherwise set `force_destroy = false` and drain the bucket deliberately. State files stay on the engineeer's disk (`*.tfstate` is gitignored); back up and remove them as part of engagement closeout.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Validation error: tenant_id must contain only lowercase letters, digits, and hyphens` | Input contained underscores, spaces, or symbols after normalization | Use `acme-corp` style identifiers; the CLI normalizes case and whitespace for you |
| `Validation error: vpc_cidr prefix must be between /16 and /24` | A `/8` (or narrower than `/24`) block was supplied | Pick a bounded block such as `10.20.0.0/16` |
| `no valid credential sources` from terraform plan/apply | No AWS credentials in the environment | Configure `AWS_PROFILE` or standard credential chain; CI intentionally never applies |
| `terraform: command not found` | Terraform not installed or not on PATH | Install Terraform >= 1.6.0 and retry |
| `Error: Bucket name already exists` or name-length errors | S3 names are global and capped at 63 characters | Change `project_name`/`tenant_id`; names derive from `<project>-<tenant>-<env>-ingest-logs` |
| `Unsupported Terraform Core version` | Terraform older than 1.6.0 | Upgrade Terraform |
| `Error: Invalid CIDR block` at plan time | CIDR failed Terraform-side validation despite passing the CLI | Re-run the CLI so the tfvars file is regenerated; both layers must agree |

## Repo layout

```
tenant-forge-cli/
├── pyproject.toml                  # package metadata; entrypoint: tenant-forge
├── src/tenant_forge/
│   ├── generator.py                # validation + tfvars generation
│   └── cli.py                      # Typer app: onboard / version
├── tests/test_generator.py         # pytest suite (validation + file creation)
├── terraform/
│   ├── main.tf / variables.tf / outputs.tf
│   └── modules/tenant_env/         # VPC, private subnet, S3 ingest bucket
├── tenants/example-acme.tfvars     # tracked example
└── .github/workflows/ci.yml        # pytest + terraform fmt/init/validate
```

## License

MIT. See [LICENSE](LICENSE).
