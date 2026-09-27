# n8n workflows as code

Two production-style n8n workflows, written and version-controlled as code rather than clicked together in the editor. Written by Micole Kurt T. Gonda — every file in this repository is my own work.

## support-triage/ — AI inbox triage
`workflow.sdk.js`, built with the n8n Workflow SDK (19 nodes).

- Polls a shared Gmail inbox, normalises each message, and de-duplicates against a record of processed message IDs so nothing is handled twice.
- A classifier (gpt-4o-mini, temperature 0) returns strict JSON through a schema parser: one of six categories, a confidence score, a one-line summary, the language, and a human-review flag for legal threats, chargebacks, security incidents, data-deletion requests or anything unsafe to answer without internal data.
- A second model drafts a reply in the customer's language; it may not invent prices, policies or dates or promise a refund, and leaves placeholders where specifics are needed.
- **Routing is deliberately not the model's decision:** a code node applies fixed business rules (confidence below 0.8, any refund request, very short messages, a failed draft), so escalation is deterministic and editable.
- Both model calls retry and then fall through to manual triage instead of failing silently; prompts treat the email as data, so instructions hidden inside a message are ignored. Flagged items post a Slack alert with the reason.

## lead-intake/ — score, route, store
- `build_workflow.py` generates the workflow JSON, so the workflow itself is reviewable, diffable code.
- `lead-intake-workflow.json` is the generated workflow; `schema.sql` is the Postgres table it writes to.
- A form trigger feeds a Code node that validates the submission and scores the lead (corporate vs free-mail domain, market tier, service interest, budget). A Switch routes it down one of three branches; each upserts to Postgres, so a resubmission updates rather than duplicates, and writes a row to Google Sheets for the team.

## Notes
Credentials are named placeholders (`newCredential(...)`), and the Google Sheet ID and webhook ID are replaced with dummy values. Import into your own n8n instance and attach your own credentials to run them.
