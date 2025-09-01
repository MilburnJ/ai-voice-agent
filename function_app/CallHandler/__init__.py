import azure.functions as func
from twilio.twiml.voice_response import VoiceResponse, Gather
from urllib.parse import parse_qs, urlencode, quote_plus

# ---- helpers ---------------------------------------------------------------
def parse_form(req: func.HttpRequest) -> dict:
    body = req.get_body().decode(errors="ignore") or ""
    params = {k: v[0] for k, v in parse_qs(body).items()}
    # querystring can also carry state
    for k, v in (req.params or {}).items():
        params.setdefault(k, v)
    return params

def say_and_hangup(text: str) -> func.HttpResponse:
    vr = VoiceResponse()
    vr.say(text)
    vr.hangup()
    return func.HttpResponse(str(vr), mimetype="application/xml")

def gather_speech(prompt: str, action_path: str, qs: dict) -> func.HttpResponse:
    vr = VoiceResponse()
    g = Gather(
        input="speech",
        action=f"{action_path}?{urlencode(qs)}" if qs else action_path,
        method="POST",
        language="en-US",
        speech_timeout="auto"
    )
    g.say(prompt)
    vr.append(g)
    # fallback if no speech heard
    vr.say("Sorry, I didn't catch that.")
    vr.redirect(f"{action_path}?{urlencode(qs)}" if qs else action_path)
    return func.HttpResponse(str(vr), mimetype="application/xml")

# ---- main ------------------------------------------------------------------
def main(req: func.HttpRequest) -> func.HttpResponse:
    P = parse_form(req)
    step = (P.get("step") or "").lower()
    speech = (P.get("SpeechResult") or "").strip()

    # Entry: greet and ask for name
    if not step:
        return gather_speech(
            prompt="Hi! Thanks for calling. I am an AI Voice Agent for Aurora Healthcare.What is your name?",
            action_path="/api/call-handler",
            qs={"step": "got_name"},
        )

    # Step 1: got_name -> ask for date
    if step == "got_name":
        caller_name = speech or P.get("name") or ""
        if not caller_name:
            return gather_speech(
                prompt="Sorry, I didn't get your name. Please say your first and last name.",
                action_path="/api/call-handler",
                qs={"step": "got_name"},
            )
        return gather_speech(
            prompt=f"Nice to meet you, {caller_name}. What date works best for your appointment?",
            action_path="/api/call-handler",
            qs={"step": "got_date", "name": caller_name},
        )

    # Step 2: got_date -> ask for time
    if step == "got_date":
        caller_name = P.get("name", "")
        appt_date = speech or P.get("date") or ""
        if not appt_date:
            return gather_speech(
                prompt="Sorry, I didn't get the date. Please say the best date for your appointment.",
                action_path="/api/call-handler",
                qs={"step": "got_date", "name": caller_name},
            )
        return gather_speech(
            prompt=f"Great. What time on {appt_date} works best?",
            action_path="/api/call-handler",
            qs={"step": "got_time", "name": caller_name, "date": appt_date},
        )

    # Step 3: got_time -> confirm summary
    if step == "got_time":
        caller_name = P.get("name", "")
        appt_date = P.get("date", "")
        appt_time = speech or P.get("time") or ""
        if not appt_time:
            return gather_speech(
                prompt=f"Sorry, I didn't get the time. What time on {appt_date} works best?",
                action_path="/api/call-handler",
                qs={"step": "got_time", "name": caller_name, "date": appt_date},
            )
        summary = f"Just to confirm, {caller_name}, you want an appointment on {appt_date} at {appt_time}. Is that correct? Please say yes or no."
        return gather_speech(
            prompt=summary,
            action_path="/api/call-handler",
            qs={"step": "confirm", "name": caller_name, "date": appt_date, "time": appt_time},
        )

    # Step 4: confirm -> finalize
    if step == "confirm":
        caller_name = P.get("name", "")
        appt_date = P.get("date", "")
        appt_time = P.get("time", "")
        answer = (speech or "").lower()
        if any(w in answer for w in ["yes", "yeah", "yep", "correct", "confirm"]):
            # TODO: save to storage/DB if you want
            return say_and_hangup(f"Awesome. {caller_name}, you're booked for {appt_date} at {appt_time}. See you then. Goodbye.")
        if any(w in answer for w in ["no", "nope", "incorrect", "cancel"]):
            return say_and_hangup("Okay, I won't book that. If you'd like to try again, please call back. Goodbye.")
        # unclear answer -> re-ask
        return gather_speech(
            prompt=f"Sorry, I didn't get that. Do you confirm the appointment for {appt_date} at {appt_time}? Please say yes or no.",
            action_path="/api/call-handler",
            qs={"step": "confirm", "name": caller_name, "date": appt_date, "time": appt_time},
        )

    # Fallback
    return say_and_hangup("Sorry, something went wrong. Please call again.")
