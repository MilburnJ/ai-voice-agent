# Azure Provisioning (CLI)

> Minimal commands to stand up Speech, OpenAI, Functions, Key Vault, and App Insights.
> Replace values as needed.

```bash
AZ_RG=rg-voice-agent
AZ_LOC=eastus
AZ_FN=fn-voice-agent
AZ_SA=stvoice$RANDOM
AZ_KV=kv-voice-agent-$RANDOM
AZ_APPINS=appi-voice-agent
AZ_SPEECH=sp-voice-agent

az group create -n $AZ_RG -l $AZ_LOC

# Speech
az cognitiveservices account create -g $AZ_RG -n $AZ_SPEECH -l $AZ_LOC   --kind SpeechServices --sku S0 --yes

# Storage + Functions (Python)
az storage account create -g $AZ_RG -n $AZ_SA -l $AZ_LOC --sku Standard_LRS
az functionapp create -g $AZ_RG -n $AZ_FN --storage-account $AZ_SA   --consumption-plan-location $AZ_LOC --functions-version 4 --runtime python

# App Insights
az monitor app-insights component create -g $AZ_RG -l $AZ_LOC -a $AZ_APPINS
az functionapp update -g $AZ_RG -n $AZ_FN --set   applicationInsights.key=$(az monitor app-insights component show -g $AZ_RG -a $AZ_APPINS --query instrumentationKey -o tsv)

# Key Vault
az keyvault create -g $AZ_RG -n $AZ_KV -l $AZ_LOC
FN_MI=$(az functionapp identity assign -g $AZ_RG -n $AZ_FN --query principalId -o tsv)
az keyvault set-policy -n $AZ_KV --object-id $FN_MI --secret-permissions get list

# Store secrets (examples)
az keyvault secret set --vault-name $AZ_KV --name SPEECH_REGION --value $AZ_LOC
az keyvault secret set --vault-name $AZ_KV --name SPEECH_KEY --value "<speech-key>"
az keyvault secret set --vault-name $AZ_KV --name OPENAI_API_KEY --value "<aoai-key>"
az keyvault secret set --vault-name $AZ_KV --name OPENAI_ENDPOINT --value "https://<your-aoai>.openai.azure.com/"
az keyvault secret set --vault-name $AZ_KV --name TWILIO_AUTH_TOKEN --value "<twilio-auth-token>"
az keyvault secret set --vault-name $AZ_KV --name STORAGE_CONN_STR --value "<storage-connection-string>"
```
