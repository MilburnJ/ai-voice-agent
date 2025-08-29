import os
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.storage.blob import BlobServiceClient, ContentSettings

def is_truthy(v: str) -> bool:
    return str(v).strip().lower() in {"1","true","yes","on"}

def _kv():
    kv_uri = os.environ.get("KEYVAULT_URI")
    if not kv_uri:
        return None
    cred = DefaultAzureCredential(exclude_shared_token_cache_credential=True)
    return SecretClient(vault_url=kv_uri, credential=cred)

def _get(k, default=None):
    client = _kv()
    if client:
        try:
            return client.get_secret(k).value
        except Exception:
            return default
    return os.environ.get(k, default)

def synthesize_and_store_tts(text: str) -> str:
    """Optional: Azure Speech synth to Blob, return HTTPS URL for Twilio <Play>.
    Requires secrets: SPEECH_KEY, SPEECH_REGION, STORAGE_CONN_STR, STORAGE_CONTAINER (public or SAS).
    """
    try:
        import azure.cognitiveservices.speech as speechsdk
    except Exception:
        return None

    speech_key = _get("SPEECH_KEY")
    speech_region = _get("SPEECH_REGION")
    conn_str = _get("STORAGE_CONN_STR")
    container = _get("STORAGE_CONTAINER", "voice-audio")

    if not all([speech_key, speech_region, conn_str]):
        return None

    # Synthesize to memory
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
    audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=False)
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    result = synthesizer.speak_text_async(text).get()
    if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        return None
    audio_data = result.audio_data

    # Upload to Blob
    bsc = BlobServiceClient.from_connection_string(conn_str)
    container_client = bsc.get_container_client(container)
    try:
        container_client.create_container(public_access="blob")
    except Exception:
        pass
    blob_name = f"tts-{abs(hash(text))}.wav"
    blob_client = container_client.get_blob_client(blob_name)
    blob_client.upload_blob(audio_data, overwrite=True, content_settings=ContentSettings(content_type="audio/wav"))
    return blob_client.url
