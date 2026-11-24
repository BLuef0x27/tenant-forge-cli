"""TenantForge: customer tenant onboarding CLI and Terraform scaffolding.

TenantForge provisions isolated, security-baselined AWS environments for
individual customer tenants. The Python package drives input validation
and the onboarding workflow; the terraform/ directory contains the
infrastructure as code that materializes each tenant environment.
"""

__version__ = "0.1.0"
