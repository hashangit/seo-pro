# workflow
- Store plan files in the project-local `.commandcode/plan/` directory, not in a global home directory path. Confidence: 0.65
- When debugging, trace existing code-level relationships to identify root causes rather than adding new code. Follow the breadcrumb trail from callers to callees. Confidence: 0.75
- After fixing one issue, continue investigating for other overlooked potential issues before declaring the problem solved. Confidence: 0.70
- When identifying code duplication, first determine if both instances are needed, then identify which pattern aligns with the codebase standard, then consolidate to that pattern before fixing the underlying issue. Confidence: 0.75
- Do not keep servers running after changes are made — the user prefers to manage their own server processes so they can restart when code changes. Kill servers instead of leaving them running. Confidence: 0.80
- When fixing a bug in one code path, check all parallel/analogous paths for the same issue (e.g., if `run_individual_analysis` needs a fix, `run_page_audit_analysis` likely needs it too). Confidence: 0.70
