import os
import json
import azure.functions as func
from twilio.twiml.voice_response import VoiceResponse
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from openai import AzureOpenAI

# Optional Azure Speech (for TTS)
from .storage_helpers import synthesize_and_store_tts, is_truthy

# Environment
KEYVAULT_URI = os.environ.get("KEYVAULT_URI")  # e.g., https://kv-voice-agent-123.vault.azure.net/
USE_AZURE_TTS = is_truthy(os.environ.get("USE_AZURE_TTS", "false"))
AOAI_DEPLOYMENT = os.environ.get("AOAI_DEPLOYMENT", "gpt-4o-mini")

def _get_secret_client():
    if not KEYVAULT_URI:
        return None
    cred = DefaultAzureCredential(exclude_shared_token_cache_credential=True)
    return SecretClient(vault_url=KEYVAULT_URI, credential=cred)

def _get_aoai_client():
    client = _get_secret_client()
    if client:
        api_key = client.get_secret("OPENAI_API_KEY").value
        endpoint = client.get_secret("OPENAI_ENDPOINT").value
    else:
        api_key = os.environ.get("OPENAI_API_KEY")
        endpoint = os.environ.get("OPENAI_ENDPOINT")

    return AzureOpenAI(api_key=api_key, api_version="2024-02-15-preview", azure_endpoint=endpoint)

def _reply_text(user_text: str) -> str:
    aoai = _get_aoai_client()
    messages = [
        {"role": "system", "content": "You are an appointment scheduler. Collect date, time, name, and confirm."},
        {"role": "user", "content": user_text or "Hello"}
    ]
    out = aoai.chat.completions.create(model=AOAI_DEPLOYMENT, messages=messages)
    return out.choices[0].message.content

def main(req: func.HttpRequest) -> func.HttpResponse:
    # Twilio may pass transcription via 'SpeechResult' for gather; otherwise read Body/params
    user_input = req.params.get("SpeechResult") or req.params.get("speechResult") or req.get_body().decode(errors="ignore")

    ai_text = _reply_text(user_input)

    vr = VoiceResponse()
    if USE_AZURE_TTS:
        # Synthesize via Azure Speech and host in Blob; Twilio plays the URL
        audio_url = synthesize_and_store_tts(ai_text)
        if audio_url:
            vr.play(audio_url)
        else:
            vr.say(ai_text)
    else:
        # Basic path uses Twilio <Say> (quick start)
        vr.say(ai_text)

    return func.HttpResponse(str(vr), mimetype="application/xml")
