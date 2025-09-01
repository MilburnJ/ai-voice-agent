# ===============================
# Azure Provisioning (PowerShell)
# Minimal commands to stand up Speech, (optional) Azure OpenAI, Functions,
# Key Vault, and Application Insights.
# Replace values as needed.
# ===============================

# ---- Login & Subscription ----
az login
az account set --subscription "<YOUR_SUBSCRIPTION_ID_OR_NAME>"

# ---- Variables ----
$AZ_RG      = "rg-voice-agent"
$AZ_LOC     = "eastus"                  # pick a region with Speech (and Azure OpenAI if you’ll use it)
$AZ_FN      = "fn-voice-agent"
$AZ_SA      = ("stvoice{0}" -f (Get-Random))        # storage account: must be globally unique, lowercase/numbers only
$AZ_KV      = ("kv-voice-agent-{0}" -f (Get-Random))# key vault: must be globally unique
$AZ_APPINS  = "appi-voice-agent"
$AZ_SPEECH  = "sp-voice-agent"

# ---- Resource Group ----
az group create -n $AZ_RG -l $AZ_LOC

# ---- Speech (STT/TTS) ----
az cognitiveservices account create `
  -g $AZ_RG -n $AZ_SPEECH -l $AZ_LOC `
  --kind SpeechServices --sku S0 --yes

# ---- Storage + Function App (Python) ----
az storage account create -g $AZ_RG -n $AZ_SA -l $AZ_LOC --sku Standard_LRS

Explicity pass subscription if this fails - ex: --subscription "Azure subscription 1"

az functionapp create `
  -g $AZ_RG -n $AZ_FN --storage-account $AZ_SA `
  --consumption-plan-location $AZ_LOC `
  --os-type Linux `
  --runtime python `
  --runtime-version 3.11 `
  --functions-version 4


# ---- Application Insights ----

# Create Temp File
$propsFile = "$env:TEMP\appi-props.json"
@'
{
  "Application_Type": "web"
}
'@ | Out-File -FilePath $propsFile -Encoding ascii

# Create Application Insights (no extension required)

az resource create `
  --resource-group $AZ_RG `
  --name $AZ_APPINS `
  --resource-type "Microsoft.Insights/components" `
  --location $AZ_LOC `
  --properties @$propsFile

# Get the connection string (preferred over instrumentation key)
$AI_CONN = az resource show `
  -g $AZ_RG -n $AZ_APPINS `
  --resource-type "Microsoft.Insights/components" `
  --query properties.ConnectionString -o tsv

# Attach to your Function App
az functionapp config appsettings set -g $AZ_RG -n $AZ_FN `
  --settings APPLICATIONINSIGHTS_CONNECTION_STRING="$AI_CONN"

# ---- Key Vault + Function Managed Identity access ----
az keyvault create -g $AZ_RG -n $AZ_KV -l $AZ_LOC

# 
$FN_MI = az functionapp identity assign -g $AZ_RG -n $AZ_FN --query principalId -o tsv

# Get the vault resource ID (scope for the role assignment)
$VAULT_ID = az keyvault show -g $AZ_RG -n $AZ_KV --query id -o tsv

# Assign RBAC role that allows getting/listing secrets
az role assignment create `
  --assignee-object-id $FN_MI `
  --assignee-principal-type ServicePrincipal `
  --role "Key Vault Secrets User" `
  --scope $VAULT_ID

# Set User perms to read/write secrets:

# Vault resource ID (scope)
$VAULT_ID = az keyvault show -g $AZ_RG -n $AZ_KV --query id -o tsv

$ME_OBJID = az ad signed-in-user show --query id -o tsv

az role assignment create `
  --assignee-object-id $ME_OBJID `
  --assignee-principal-type User `
  --role "Key Vault Secrets Officer" `
  --scope $VAULT_ID

# ---- Store Secrets in Key Vault (examples) ----

# 1 Speech keys/region


$SPEECH_KEY = az cognitiveservices account keys list -g $AZ_RG -n $AZ_SPEECH --query key1 -o tsv
az keyvault secret set --vault-name $AZ_KV --name SPEECH-REGION --value $AZ_LOC | Out-Null
az keyvault secret set --vault-name $AZ_KV --name SPEECH-KEY    --value $SPEECH_KEY | Out-Null

# 2 Azure OpenAI — you must have access approved and an Azure OpenAI resource created.

$AZ_OPENAI="aoai-voice-agent"
$AZ_RG="rg-voice-agent"
$AZ_LOC="eastus"   # change if eastus doesn’t show OpenAI availability

az cognitiveservices account create `
  -n $AZ_OPENAI `
  -g $AZ_RG `
  -l $AZ_LOC `
  --kind OpenAI `
  --sku S0 `
  --yes

# Deploy a model (can change the model)

Go into Azure AI foundry and deploy a model


# After creating Azure OpenAI in the Portal, set the endpoint/key here:

 az keyvault secret set --vault-name $AZ_KV --name OPENAI-API-KEY   --value "<aoai-key>"
 az keyvault secret set --vault-name $AZ_KV --name OPENAI-ENDPOINT  --value "https://<your-aoai>.openai.azure.com/"

# 3  Twilio token (for validating requests if you plan to)
 
 az keyvault secret set --vault-name $AZ_KV --name TWILIO-AUTH-TOKEN --value "<twilio-auth-token>"

# 4 Storage connection string (needed if you’ll use Azure Speech TTS → Blob → Twilio <Play>)

# Ignore for now, going to use twilio say voice
# Used for Azure Neural voices

$ST_CONN = az storage account show-connection-string -g $AZ_RG -n $AZ_SA --query connectionString -o tsv
az keyvault secret set --vault-name $AZ_KV --name STORAGE_CONN_STR --value $ST_CONN | Out-Null
# Optionally choose a container name for audio
az keyvault secret set --vault-name $AZ_KV --name STORAGE_CONTAINER --value "voice-audio" | Out-Null

# ---- (Optional) Convenience app settings for your Function ----
# Toggle Azure TTS path (Function will synthesize to Blob and return a <Play> URL)
az functionapp config appsettings set -g $AZ_RG -n $AZ_FN --settings USE_AZURE_TTS=false | Out-Null
# If you already deployed an AOAI model name/deployment you can set it here
az functionapp config appsettings set -g $AZ_RG -n $AZ_FN --settings AOAI_DEPLOYMENT="gpt-4o-mini" | Out-Null

# ---- Final Echo of Important Values ----
"`nProvisioning complete."
"Resource Group     : $AZ_RG"
"Location           : $AZ_LOC"
"Function App       : $AZ_FN"
"Storage Account    : $AZ_SA"
"Key Vault          : $AZ_KV"
"App Insights       : $AZ_APPINS"
"Speech Resource    : $AZ_SPEECH"
"Key Vault URI      : $KEYVAULT_URI"
"`nNext steps:"
"- Deploy your Function code (func azure functionapp publish $AZ_FN) or via GitHub Actions."
"- In Twilio Console → Phone Numbers → set Voice webhook to:"
"  https://$AZ_FN.azurewebsites.net/api/call-handler"
"- If using Azure TTS: set USE_AZURE_TTS=true and make sure STORAGE_CONN_STR/CONTAINER are in Key Vault."
