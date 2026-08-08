from enum import Enum


class Role(str, Enum):
    ORGANISATION_ADMIN = "organisation_admin"
    VERIFICATION_EXECUTIVE = "verification_executive"
    FRAUD_ANALYST = "fraud_analyst"
    REVIEWER = "reviewer"
    SENIOR_APPROVER = "senior_approver"
    AUDITOR = "auditor"
    API_CLIENT = "api_client"
    SYSTEM_ADMIN = "system_admin"


class Permission(str, Enum):
    ORGANISATION_MANAGE = "organisation:manage"
    CASE_SUBMIT = "case:submit"
    CASE_VIEW = "case:view"
    HIGH_RISK_ANALYSE = "high_risk:analyse"
    FINDING_REVIEW = "finding:review"
    SECOND_LEVEL_APPROVE = "approval:second_level"
    AUDIT_VIEW = "audit:view"
    INFRASTRUCTURE_MANAGE = "infrastructure:manage"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.ORGANISATION_ADMIN: frozenset(
        {
            Permission.ORGANISATION_MANAGE,
            Permission.CASE_SUBMIT,
            Permission.CASE_VIEW,
            Permission.AUDIT_VIEW,
        }
    ),
    Role.VERIFICATION_EXECUTIVE: frozenset(
        {Permission.CASE_SUBMIT, Permission.CASE_VIEW}
    ),
    Role.FRAUD_ANALYST: frozenset({Permission.CASE_VIEW, Permission.HIGH_RISK_ANALYSE}),
    Role.REVIEWER: frozenset({Permission.CASE_VIEW, Permission.FINDING_REVIEW}),
    Role.SENIOR_APPROVER: frozenset(
        {Permission.CASE_VIEW, Permission.SECOND_LEVEL_APPROVE}
    ),
    Role.AUDITOR: frozenset({Permission.AUDIT_VIEW}),
    Role.API_CLIENT: frozenset({Permission.CASE_SUBMIT}),
    Role.SYSTEM_ADMIN: frozenset({Permission.INFRASTRUCTURE_MANAGE}),
}
