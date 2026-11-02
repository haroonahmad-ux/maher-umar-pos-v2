# CI/CD automation setup

These workflows extend the existing Android build pipeline. They do not modify the application's runtime code or core architecture.

## Automated PR labels and commit categorization

- PR labels are derived from changed paths and branch prefixes using `.github/labeler.yml`.
- Push commits receive a category summary in the Actions run (feature, bug fix, docs, tests, refactor, maintenance/CI, or other). GitHub does not support native labels on individual commits, so this is recorded as an Actions summary rather than a misleading commit label.
- To request automatic PR reviewers, add the repository Actions variable `PR_REVIEWERS` as comma-separated GitHub usernames, for example `reviewer-one,reviewer-two`. Leave it unset to skip reviewer requests.

## PR quality checks

- Python project: Ruff style/common-error checks plus Python bytecode syntax compilation.
- Kotlin project: Gradle `check` and Android debug compilation.

## Supabase schema sync

BizCore is linked to Supabase project ref `dtajbsosaaohyluedcof`. Add repository Actions secrets `SUPABASE_ACCESS_TOKEN` and `SUPABASE_DB_PASSWORD`. Migration changes are dry-run checked on PRs targeting `main`; migrations are applied only after they land on `main`.

The workflow never runs a destructive database reset or seed operation. PRs only run a remote migration dry-run; production migration application is restricted to pushes to `main`.

## WhatsApp build notifications

Configure these repository **Actions secrets**:

- `WHATSAPP_ACCESS_TOKEN` — Meta WhatsApp Cloud API access token.
- `WHATSAPP_PHONE_NUMBER_ID` — Cloud API phone number ID.
- `WHATSAPP_TO` — recipient number in international digits-only format (no `+`).

Configure these repository **Actions variables**:

- `WHATSAPP_TEMPLATE_NAME` — approved WhatsApp message template name.
- `WHATSAPP_TEMPLATE_LANGUAGE` — template language code; defaults to `en_US`.
- `WHATSAPP_GRAPH_API_VERSION` — Graph API version; defaults to `v23.0`.

The approved template must have five body text placeholders in this exact order: repository, workflow name, build result, branch, and Actions run URL. The notification job is integrated into the existing APK workflow and sends a template message after success or failure. If credentials are not configured, it safely skips the send and records the missing setup in the run summary.

## Security notes

- Credentials are referenced only through GitHub Actions secrets; no tokens or database passwords are committed.
- Workflows use least-privilege repository permissions where practical.
- Production database migrations are serialized and only applied from `main`.
- Reviewers and WhatsApp destinations are configured per repository, not hard-coded into source.
