## Phone Agent — Quick Start (Non‑Technical Guide)

This guide helps you make a phone agent talk on a real call in minutes. No deep technical knowledge needed.

### What you’ll do
- **Prepare Galtea**: Create a Test (your conversation premise) and a Version (to track your agent build).
- **Start the server**: Run the phone agent locally.
- **Point Twilio to your server**: So calls can reach your agent.
- **Run a simple simulator**: Automatically place a call and have a conversation.

---

### 1) Before you start: Set up Galtea
- **Create a Test** in Galtea.
  - **Purpose**: This defines the scenario/premise your conversation should follow (e.g., appointment booking, support intake).
  - **Output**: You’ll get a `test_id`.
- **Create a Version** in Galtea.
  - **Purpose**: Track which agent model/settings you are testing.
  - **Output**: You’ll get a `version_id`.

You’ll paste both `test_id` and `version_id` into the app’s `config.yaml` later.

---

### 2) Prerequisites
- **Twilio** account with a phone number you can use.
- **ElevenLabs** API key (for speech‑to‑text and text‑to‑speech).
- **Galtea** API key.
- **ngrok** or similar to expose your local server to the internet.
- **Conda** (recommended) or Python 3.10.

---

### 3) Install the app
```bash
git clone <your_repo_url>
cd phone
conda env create -f environment.yml
conda activate phone
```

Create a `.env` file in the `phone` folder with your secrets:
```bash
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_twilio_auth_token
ELEVENLABS_API_KEY_GAL=your_elevenlabs_api_key
API_KEY=choose_a_simple_password_for_local_use
GALTEA_API_KEY_DEV=your_galtea_api_key
```

---

### 4) Start the server
```bash
uvicorn agent_twilio:app --host 0.0.0.0 --port 8001
```
Leave this running.

In a new terminal, expose the server publicly:
```bash
ngrok http 8001
```
Copy the HTTPS forwarding URL shown by ngrok (looks like `https://<something>.ngrok-free.app`).

---

### 5) Point Twilio to your server
In the Twilio Console → Phone Numbers → select your number → Voice settings:
- Set “A CALL COMES IN” to **Webhook** (HTTP POST)
- URL: `https://<your-ngrok-subdomain>.ngrok-free.app/twilio-voice`
Save.

---

### 6) Fill in `config.yaml`
Open `config.yaml` and update the following:
```yaml
remote_url: "https://<your-ngrok>.ngrok-free.app"  # from ngrok
base_url: "http://localhost:8001"                  # leave as is
from_number: "+1YOUR_TWILIO_NUMBER"               # your Twilio number (E.164)
to_number: "+1DESTINATION_NUMBER"                  # number to call (can be your mobile)
test_id: "<your_galtea_test_id>"                   # from Step 1
version_id: "<your_galtea_version_id>"             # from Step 1
tests: [0]                                          # which Galtea test indices to run
asycio_timeout: 120.0
request_timeout: 120.0
talk_timeout: 80
max_turns: 12
agent_goes_first: true
```

Tip: If your Test has multiple cases, `tests: [0,1,2]` will run those indices.

---

### 7) Make the call with the simulator
With your server still running, in a new terminal:
```bash
conda activate phone
python talk.py
```
What happens now:
- The simulator starts a real Twilio call from `from_number` to `to_number`.
- Your agent waits for you to speak, then replies with a synthetic voice.
- This repeats until the conversation finishes or times out.

---

### How the conversation flows (simple)
- **You speak** → the agent listens and waits a brief moment when you stop.
- **It transcribes** what you said and **generates a reply**.
- **It speaks back** to you using ElevenLabs voice.
- The process repeats up to `max_turns` or until the call ends.

Notes:
- The current setup uses Spanish for STT/TTS. You can switch languages in `agent_twilio.py` later (optional).

---

### Quick fixes if things don’t work
- **No audio / no response**:
  - Confirm your Twilio webhook URL matches your current ngrok URL.
  - Ensure the server (`uvicorn ...`) is running.
- **Forbidden (403) from /generate**:
  - Make sure your `.env` `API_KEY` matches what the app expects (header `x-api-key`).
- **Timeouts (204)**:
  - Speak clearly on the call; try increasing `asycio_timeout` or `talk_timeout` in `config.yaml`.
- **Ngrok URL changed**:
  - Update both Twilio webhook and `remote_url` in `config.yaml`.

---

### Ending and re-running
- If you stop the simulator or server, the app tries to end the Twilio call cleanly.
- When you restart ngrok, update your Twilio webhook and `config.yaml`.

---

### Where to change voices or language (optional)
- Open `agent_twilio.py` and look for ElevenLabs settings for STT (`language_code`) and TTS (`language_code`, `voice_id`, `model_id`).

That’s it! You now have a working phone agent that can talk on a real call, using your Galtea Test/Version for scenario control.


