# Azure-First Voice Agent (Inbound Calls)

**Goal:** Maximize Azure-native services; Twilio only for PSTN entry.
- Azure Functions (HTTP trigger) — orchestrator
- Azure OpenAI — dialog & appointment logic
- Azure Speech — STT/TTS (optional first pass uses Twilio <Say>, enable Azure TTS later)
- Azure Key Vault — secrets
- Azure Storage/Cosmos (optional) — store transcripts/appointments
- Application Insights — logging/metrics

## Quick start

### 0) Provision Azure resources (CLI)
See `README_AZURE.md` for end-to-end CLI commands.

### 1) Configure local settings (development)
Copy `function_app/local.settings.json.template` → `function_app/local.settings.json` and fill the values or run with Key Vault references in Azure.

### 2) Run locally
```bash
cd function_app
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
func start
```

### 3) Deploy
Use the included GitHub Actions workflow or:
```bash
func azure functionapp publish <YOUR_FUNCTION_APP_NAME>
```

### 4) Twilio webhook
Point your Twilio number's Voice webhook to:
```
https://<YOUR_FUNCTION_APP>.azurewebsites.net/api/call-handler
```
For a fully Azure voice path, enable Azure Speech TTS (writes an MP3 to Blob and returns a TwiML <Play> URL).

---

## Toggle: Azure TTS vs Twilio <Say>
- Default = Twilio `<Say>` for simplicity
- Set `USE_AZURE_TTS=true` to synthesize via Azure Speech and play via `<Play>`

---

## Folder layout
```
.
├── .github/workflows/azure-functions-deploy.yml
├── function_app/
│   ├── __init__.py
│   ├── function.json
│   ├── host.json
│   ├── requirements.txt
│   ├── local.settings.json.template
│   └── storage_helpers.py
├── backend/conversation_script.txt
├── README_AZURE.md
└── LICENSE
```
