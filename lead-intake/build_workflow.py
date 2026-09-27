import json, uuid

CODE = r'''// ---------------------------------------------------------------
// Lead validation, enrichment and scoring.
// Runs once for ALL items so one form submission = one clean lead.
// ---------------------------------------------------------------
const FREE_MAIL = ['gmail.com','yahoo.com','hotmail.com','outlook.com','icloud.com','aol.com','proton.me'];
const TIER1 = ['United States','Canada','United Kingdom','Australia','Singapore'];
const SERVICE_POINTS = {
  'Ongoing Retainer': 25,
  'Automation Build': 20,
  'Consultation': 10,
  'General Inquiry': 5,
};

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[a-z]{2,}$/i;

const results = [];

for (const item of $input.all()) {
  const f = item.json;

  const name    = String(f['Full Name'] ?? '').trim();
  const email   = String(f['Work Email'] ?? '').trim().toLowerCase();
  const company = String(f['Company'] ?? '').trim();
  const country = String(f['Country'] ?? '').trim();
  const service = String(f['Service Interest'] ?? '').trim();
  const notes   = String(f['Project Notes'] ?? '').trim();
  const budget  = Number(f['Monthly Budget (USD)'] ?? 0);

  // --- validation -------------------------------------------------
  const errors = [];
  if (name.length < 2)       errors.push('name_too_short');
  if (!EMAIL_RE.test(email)) errors.push('invalid_email');
  if (company.length < 2)    errors.push('company_missing');
  if (!Number.isFinite(budget) || budget < 0) errors.push('invalid_budget');

  const domain = email.includes('@') ? email.split('@')[1] : '';
  const isCorporate = domain !== '' && !FREE_MAIL.includes(domain);

  // --- scoring ----------------------------------------------------
  let score = 0;
  if (budget >= 5000)      score += 50;
  else if (budget >= 2000) score += 35;
  else if (budget >= 500)  score += 20;
  else                     score += 5;

  score += SERVICE_POINTS[service] ?? 0;
  if (TIER1.includes(country)) score += 15;
  if (isCorporate)             score += 10;
  if (notes.length > 80)       score += 10;
  score = Math.min(score, 100);

  const tier = score >= 70 ? 'hot' : score >= 40 ? 'warm' : 'cold';

  results.push({
    json: {
      lead_id: 'LD-' + Date.now() + '-' + Math.random().toString(36).slice(2, 7).toUpperCase(),
      submitted_at: new Date().toISOString(),
      full_name: name,
      email: email,
      email_domain: domain,
      is_corporate_email: isCorporate,
      company: company,
      country: country,
      service_interest: service,
      monthly_budget: budget,
      notes: notes,
      lead_score: score,
      lead_tier: tier,
      is_valid: errors.length === 0,
      validation_errors: errors.join(', '),
    },
  });
}

return results;
'''


def uid():
    return str(uuid.uuid4())


def cond_bool(left):
    return {
        "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 2},
        "conditions": [{
            "id": uid(),
            "leftValue": left,
            "rightValue": "",
            "operator": {"type": "boolean", "operation": "true", "singleValue": True},
        }],
        "combinator": "and",
    }


def cond_str_eq(left, right):
    return {
        "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 2},
        "conditions": [{
            "id": uid(),
            "leftValue": left,
            "rightValue": right,
            "operator": {"type": "string", "operation": "equals"},
        }],
        "combinator": "and",
    }


SHEET_URL = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit"


def sheet_node(name, tab, pos, cols):
    return {
        "parameters": {
            "operation": "append",
            "documentId": {"__rl": True, "mode": "url", "value": SHEET_URL},
            "sheetName": {"__rl": True, "mode": "name", "value": tab},
            "columns": {
                "mappingMode": "defineBelow",
                "value": cols,
                "matchingColumns": [],
                "schema": [],
                "attemptToConvertTypes": False,
                "convertFieldsToString": False,
            },
            "options": {},
        },
        "type": "n8n-nodes-base.googleSheets",
        "typeVersion": 4.5,
        "position": pos,
        "id": uid(),
        "name": name,
    }


def pg_node(name, pos, extra):
    base = {
        "lead_id": "={{ $json.lead_id }}",
        "full_name": "={{ $json.full_name }}",
        "email": "={{ $json.email }}",
        "company": "={{ $json.company }}",
        "country": "={{ $json.country }}",
        "service_interest": "={{ $json.service_interest }}",
        "monthly_budget": "={{ $json.monthly_budget }}",
        "lead_score": "={{ $json.lead_score }}",
        "lead_tier": "={{ $json.lead_tier }}",
        "notes": "={{ $json.notes }}",
    }
    base.update(extra)
    return {
        "parameters": {
            "operation": "upsert",
            "schema": {"__rl": True, "mode": "list", "value": "public"},
            "table": {"__rl": True, "mode": "list", "value": "leads"},
            "columns": {
                "mappingMode": "defineBelow",
                "value": base,
                "matchingColumns": ["email"],
                "schema": [],
                "attemptToConvertTypes": False,
                "convertFieldsToString": False,
            },
            "options": {},
        },
        "type": "n8n-nodes-base.postgres",
        "typeVersion": 2.5,
        "position": pos,
        "id": uid(),
        "name": name,
    }


SHEET_COLS_FULL = {
    "Lead ID": "={{ $json.lead_id }}",
    "Submitted At": "={{ $json.submitted_at }}",
    "Name": "={{ $json.full_name }}",
    "Email": "={{ $json.email }}",
    "Company": "={{ $json.company }}",
    "Country": "={{ $json.country }}",
    "Service": "={{ $json.service_interest }}",
    "Budget": "={{ $json.monthly_budget }}",
    "Score": "={{ $json.lead_score }}",
    "Tier": "={{ $json.lead_tier }}",
    "Owner": "={{ $json.assigned_to }}",
}

SHEET_COLS_COLD = {k: v for k, v in SHEET_COLS_FULL.items() if k != "Owner"}

nodes = [
    {
        "parameters": {
            "formTitle": "Lion Sales Funnel - Project Enquiry",
            "formDescription": "Tell us about your project and a strategist will get back to you.",
            "formFields": {"values": [
                {"fieldLabel": "Full Name", "requiredField": True},
                {"fieldLabel": "Work Email", "fieldType": "email", "requiredField": True},
                {"fieldLabel": "Company", "requiredField": True},
                {"fieldLabel": "Monthly Budget (USD)", "fieldType": "number", "requiredField": True},
                {"fieldLabel": "Country", "fieldType": "dropdown", "fieldOptions": {"values": [
                    {"option": "United States"}, {"option": "Canada"}, {"option": "United Kingdom"},
                    {"option": "Australia"}, {"option": "Singapore"}, {"option": "Philippines"},
                    {"option": "India"}, {"option": "Other"}]}, "requiredField": True},
                {"fieldLabel": "Service Interest", "fieldType": "dropdown", "fieldOptions": {"values": [
                    {"option": "Ongoing Retainer"}, {"option": "Automation Build"},
                    {"option": "Consultation"}, {"option": "General Inquiry"}]}, "requiredField": True},
                {"fieldLabel": "Project Notes", "fieldType": "textarea"},
            ]},
            "options": {},
        },
        "type": "n8n-nodes-base.formTrigger",
        "typeVersion": 2.2,
        "position": [-660, 300],
        "id": uid(),
        "name": "Form Submission",
        "webhookId": uid(),
    },
    {
        "parameters": {"jsCode": CODE},
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [-440, 300],
        "id": uid(),
        "name": "Validate, Enrich & Score",
    },
    {
        "parameters": {"conditions": cond_bool("={{ $json.is_valid }}"), "options": {}},
        "type": "n8n-nodes-base.if",
        "typeVersion": 2.2,
        "position": [-220, 300],
        "id": uid(),
        "name": "IF Submission Valid",
    },
    {
        "parameters": {
            "rules": {"values": [
                {"conditions": cond_str_eq("={{ $json.lead_tier }}", "hot"), "renameOutput": True, "outputKey": "Hot"},
                {"conditions": cond_str_eq("={{ $json.lead_tier }}", "warm"), "renameOutput": True, "outputKey": "Warm"},
                {"conditions": cond_str_eq("={{ $json.lead_tier }}", "cold"), "renameOutput": True, "outputKey": "Cold"},
            ]},
            "options": {},
        },
        "type": "n8n-nodes-base.switch",
        "typeVersion": 3.2,
        "position": [20, 200],
        "id": uid(),
        "name": "Route By Lead Tier",
    },
    {
        "parameters": {},
        "type": "n8n-nodes-base.noOp",
        "typeVersion": 1,
        "position": [20, 520],
        "id": uid(),
        "name": "Discard Invalid Submission",
    },
    pg_node("Postgres - Upsert Hot Lead", [280, 40], {"status": "sales_queue", "assigned_to": "senior-closer"}),
    pg_node("Postgres - Upsert Warm Lead", [280, 220], {"status": "nurture", "assigned_to": "sdr-team"}),
    sheet_node("Sheets - Priority Leads", "Priority Leads", [540, 40], SHEET_COLS_FULL),
    sheet_node("Sheets - Nurture Queue", "Nurture Queue", [540, 220], SHEET_COLS_FULL),
    sheet_node("Sheets - Cold Archive", "Cold Archive", [280, 400], SHEET_COLS_COLD),
]


def c(node):
    return {"node": node, "type": "main", "index": 0}


connections = {
    "Form Submission": {"main": [[c("Validate, Enrich & Score")]]},
    "Validate, Enrich & Score": {"main": [[c("IF Submission Valid")]]},
    "IF Submission Valid": {"main": [[c("Route By Lead Tier")], [c("Discard Invalid Submission")]]},
    "Route By Lead Tier": {"main": [
        [c("Postgres - Upsert Hot Lead")],
        [c("Postgres - Upsert Warm Lead")],
        [c("Sheets - Cold Archive")],
    ]},
    "Postgres - Upsert Hot Lead": {"main": [[c("Sheets - Priority Leads")]]},
    "Postgres - Upsert Warm Lead": {"main": [[c("Sheets - Nurture Queue")]]},
}

wf = {
    "name": "Lead Intake - Score, Route, Store",
    "nodes": nodes,
    "connections": connections,
    "pinData": {},
    "settings": {"executionOrder": "v1"},
    "meta": {"instanceId": "backend-challenge"},
}

with open("lead-intake-workflow.json", "w", encoding="utf-8") as fh:
    json.dump(wf, fh, indent=2, ensure_ascii=False)

print("nodes:", len(nodes))
