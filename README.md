## Twilio Voice with FastAPI, ElevenLabs, and Galtea (Updated)

This project enables real-time phone conversations using Twilio for call control, FastAPI for the backend, ElevenLabs for Speech-to-Text and Text-to-Speech, and an optional Galtea-driven simulator to automate test calls.

Key updates since the previous version:
- File rename: `twilio_restAPI.py` ➜ `agent_twilio.py`
- Script rename: `run_calling_agent.py` ➜ `talk.py`
- Added safety mechanisms: graceful shutdown, SIGINT/SIGTERM handlers, robust WebSocket and call cleanup, and configurable talk timeouts.

### Features
- **Real-time voice**: Handle incoming Twilio calls and stream audio via WebSocket.
- **Speech-to-Text (ElevenLabs)**: Convert caller speech to text.
- **Text-to-Speech (ElevenLabs)**: Synthesize agent replies and stream them back to Twilio.
- **Voice Activity Detection (webrtcvad)**: Detect speech/silence to trigger transcription efficiently.
- **Agent simulator (`talk.py`)**: Place a real Twilio call and orchestrate turns via `/generate`.
- **Safety and resilience**:
  - **SIGINT/SIGTERM handling** in both server and simulator to gracefully end calls.
  - **Automatic Twilio call completion** on failures/timeouts/interrupts.
  - **WebSocket closure** and shutdown signaling to avoid dangling streams.
  - **Talk timeout** to end stalled conversations.

### Important limitation
This implementation supports only one active call/session at a time. Call-specific data is stored in global `app.state` and is reset per session. To support concurrent callers, refactor to keep per-call state keyed by the Twilio `sid`/`streamSid` (e.g., a dictionary of session objects) and avoid mutating shared globals.

### Project Structure
- `agent_twilio.py`: FastAPI app handling Twilio webhooks, the media WebSocket, ElevenLabs STT/TTS, and the `/generate` API.
- `talk.py`: Galtea-powered simulator that places a Twilio call and alternates turns via `/generate`.
- `experiment/experiment.ipynb`: Optional notebook for manual testing.
- `environment.yml`: Reproducible Conda environment.
- `notes.txt`: Design notes and TODOs.

### Requirements and Setup
1) Clone and enter the repo
```bash
git clone <repository_url>
cd phone
```

2) Create the Conda environment (recommended)
```bash
conda env create -f environment.yml
conda activate phone
```
Alternatively, use a virtualenv and install packages based on imports.

3) Create a `.env` file with required secrets
```bash
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_twilio_auth_token
ELEVENLABS_API_KEY_GAL=your_elevenlabs_api_key
API_KEY=your_internal_api_key_for_generate
GALTEA_API_KEY_DEV=your_galtea_api_key   # needed for talk.py simulator
```

### Running the Server
Start the FastAPI app on port 8001:
```bash
uvicorn agent_twilio:app --host 0.0.0.0 --port 8001
```

Expose your server publicly for Twilio (e.g., with ngrok):
```bash
ngrok http 8001
```
Copy the generated HTTPS forwarding URL (e.g., `https://<subdomain>.ngrok-free.app`).

### Configure Twilio
1) In Twilio Console ➜ Phone Numbers ➜ Active numbers ➜ select your number.
2) Under Voice & Fax, set A CALL COMES IN to Webhook (HTTP POST) pointing to:
```
https://<your-ngrok-subdomain>.ngrok-free.app/twilio-voice
```
The server will respond with TwiML that instructs Twilio to open a media bidirectional WebSocket to `wss://<host>/media`.

### Driving a Call with the Simulator (`talk.py`)
`talk.py` replaces the old `run_calling_agent.py` and uses Galtea to run scripted test cases that place a real Twilio call, then alternate turns via `/generate`.

- Update the following in `talk.py` as needed:
  - **`remote_url`**: your public HTTPS host (e.g., the ngrok URL).
  - **`from_number`**: your Twilio number (E.164 format).
  - **`to_number`**: destination number (E.164 format).
- Ensure your `.env` contains `GALTEA_API_KEY_DEV`, Twilio credentials, and `API_KEY`.

Run it:
```bash
python talk.py
```
The simulator will:
- Start a Twilio call with your configured numbers.
- Make a first request to `/generate?first=true` to wait for the caller’s first utterance.
- On subsequent turns, send the agent’s text to synthesize, and wait for the next user transcription.
- On completion or interrupt, update the Twilio call status to `completed`.

### API Overview
- **POST `/twilio-voice`**
  - Twilio webhook for incoming calls. Returns TwiML that starts a bidirectional media stream to `/media`.

- **WebSocket `/media`**
  - Twilio streams u-law audio; the server converts to 16-bit PCM for VAD and STT.
  - ElevenLabs STT is invoked after silence is detected following speech.
  - Outbound TTS is generated via ElevenLabs and streamed back as u-law media frames.
  - A `mark` event named `endOfPlayback` is sent to delineate playback completion.

- **GET `/generate`** (secured via `X-API-KEY`)
  - Query params:
    - `client`: placeholder value required by current interface (not used server-side).
    - `sid`: Twilio call SID for the active call.
    - `first` (bool): if true, wait for first user transcription.
    - `timeout` (float): max seconds to wait before returning `204 No Content`.
    - `input` (str): agent text to synthesize and play to the caller.
    - `talk_timeout` (float): conversation idle timeout (seconds) for the server.
  - Responses:
    - `200`: `{ "response": "..." }` with the latest transcription or termination reason.
    - `204`: No content within the timeout window.

### Safety and Shutdown Behavior
- **Server (`agent_twilio.py`)**
  - Installs handlers for `SIGINT`/`SIGTERM`; sets a global shutdown event.
  - On Twilio `stop` events, server-side errors, WebSocket errors, talk timeout, or shutdown:
    - Signals shutdown, closes the WebSocket when appropriate.
    - Updates the Twilio call to `completed` using the stored `sid`.
  - Uses a configurable `talk_timeout` (default ~50s) to end stalled sessions.

- **Simulator (`talk.py`)**
  - Catches `SIGINT`/`SIGTERM` and ensures the active Twilio call is set to `completed` before exiting.
  - Applies request timeouts when calling `/generate` and exits cleanly on errors/timeouts.

### Tuning and Configuration
- **VAD sensitivity**: Aggressive mode (`3`) is used for webrtcvad.
- **Silence trigger**: `SILENCE_CHUNKS_TRIGGER` defaults to `140`. Increase if you need more post-speech silence before transcription.
- **Sample rate**: Audio is processed at `8000 Hz` mono, 16-bit PCM internally.
- **ElevenLabs**:
  - STT model: `scribe_v1` (example), language: `es` (Spanish).
  - TTS model: `eleven_flash_v2_5`, output: `pcm_8000`, language: `es`.
  - Adjust `voice_id`, language, and model to your use case.

### Troubleshooting
- **Ngrok URL changes**: Update Twilio webhook and `remote_url` in `talk.py` when ngrok restarts.
- **403 from `/generate`**: Ensure the `X-API-KEY` header matches `API_KEY` in `.env`.
- **204 from `/generate`**: A timeout occurred; check VAD thresholds, audio path, or increase `timeout`.
- **No audio**: Confirm that outbound media is being sent and `endOfPlayback` marks are being received.
- **Call ends early**: Check `talk_timeout` and server logs.

### Notes
- This README reflects the current codebase where `agent_twilio.py` and `talk.py` replace the old `twilio_restAPI.py` and `run_calling_agent.py`.
- The `experiment/experiment.ipynb` remains available for manual tests; ensure it targets the updated endpoints and environment.
