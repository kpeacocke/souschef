# Security Policy

## Supported Versions

Only the latest published SousChef release is supported for security fixes.
Previous releases are not maintained and may not receive security updates.

| Release | Supported |
| ------- | --------- |
| Latest release | Yes |
| Previous releases | No |

See the [GitHub releases](https://github.com/kpeacocke/souschef/releases) page
for the latest published release.

## Reporting a Vulnerability

Please do not report security vulnerabilities through public GitHub issues.
Use one of these private reporting channels:

- [Report a vulnerability through GitHub Security Advisories](https://github.com/kpeacocke/souschef/security/advisories/new)
- [Email the maintainer](mailto:krpeacocke@gmail.com)

Include a description, impact, affected SousChef version, relevant environment
details, and reproduction steps or a proof of concept where appropriate. Avoid
including real credentials or other sensitive data in a report.

Maintainers will triage reports and coordinate disclosure as available. There
is no published response or remediation service-level agreement.

## Security Considerations

- The MCP server may read and write files within its configured workspace.
  Mount only the files needed for a task, use a dedicated workspace, and apply
  host filesystem permissions appropriate to the data.
- Remote integrations can send requests or source content to configured Chef,
  Salt, Puppet, GitHub, or AI-provider endpoints. Review the endpoint, provider
  terms, and data sensitivity before enabling an integration.
- Credentials may be supplied to tools or through environment configuration.
  Do not commit credentials, place them in generated artefacts, or share them
  through public issues.
- SousChef generates migration output; review playbooks and commands before
  executing them against infrastructure.
- The GitHub Copilot-agent-named tools only change issue labels and comments;
  they do not assign, pause, stop, or resume a Copilot agent.
- Optional reasons and additional-instruction text are posted as issue comments
  and may be visible to anyone with access to the repository. Do not include
  secrets or private information in these fields.
- The v2 migration deployment, rollback, and playbook-validation tools are not
  implemented and report that no remote action or validation was performed.

## Automated Security Checks

Repository CI runs dependency auditing with `pip-audit` and CodeQL analysis.
Container CI scans for fixable HIGH and CRITICAL vulnerabilities, and release
workflows upload Trivy scan results for published MCP and UI images. These
checks reduce risk but do not guarantee that the source code, dependencies, or
images are free of vulnerabilities.
