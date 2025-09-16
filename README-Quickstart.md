## Phone Agent — Quick Start

This guide helps you make a phone agent talk on a real call in minutes. No deep technical knowledge needed.

### What you'll do
- **Prepare Galtea**: Create a Test and Version for your conversation scenario.
- **One-command setup**: Install everything you need automatically.
- **Configure secrets**: Add your API keys to `.env` file.
- **Start and test**: Run the server and place a test call.

---

### 1) Before you start: Set up Galtea
- **Create a Test** in Galtea.
  - **Purpose**: This defines the scenario/premise your conversation should follow (e.g., appointment booking, support intake).
  - **Output**: You'll get a `test_id`.
- **Create a Version** in Galtea.
  - **Purpose**: Track which agent model/settings you are testing.
  - **Output**: You'll get a `version_id`.

You'll paste both `test_id` and `version_id` into the app's `config.yaml` later.

---

### 2) Complete setup (streamlined)

#### One-command setup:
```bash
git clone <your_repo_url>
cd Calling-Agent
make dev-setup
```

This automatically:
- Installs uv (Python package manager)
- Creates a `.env` template file
- Installs all dependencies
- Shows you the next steps

#### Install ngrok (if not already installed):
```bash
make setup-ngrok
ngrok config add-authtoken <your-authtoken>  # Get token from ngrok.com
```

---

### 3) Configure your secrets
Edit the `.env` file in your project folder:
```bash
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_twilio_auth_token
ELEVENLABS_API_KEY_GAL=your_elevenlabs_api_key
API_KEY=choose_a_simple_password_for_local_use
GALTEA_API_KEY_DEV=your_galtea_api_key
```

---

### 4) Start everything and test

#### Start the server:
```bash
make run-dev
```
Leave this running in Terminal 1.

#### Expose to internet (in Terminal 2):
```bash
ngrok http 8001
```
Copy the HTTPS forwarding URL (like `https://abc123.ngrok-free.app`).

#### Configure Twilio webhook:
In the Twilio Console → Phone Numbers → your number → Voice settings:
- Set "A CALL COMES IN" to **Webhook** (HTTP POST)
- URL: `https://<your-ngrok-subdomain>.ngrok-free.app/twilio-voice`

#### Update config.yaml:
```yaml
remote_url: "https://<your-ngrok>.ngrok-free.app"  # from ngrok
base_url: "http://localhost:8001"                  # leave as is
from_number: "+1YOUR_TWILIO_NUMBER"               # your Twilio number
to_number: "+1DESTINATION_NUMBER"                  # number to call
test_id: "<your_galtea_test_id>"                   # from Step 1
version_id: "<your_galtea_version_id>"             # from Step 1
tests: [0]                                          # test cases to run
asycio_timeout: 120.0
request_timeout: 120.0
talk_timeout: 80
max_turns: 12
agent_goes_first: true
```

#### Run test call (in Terminal 3):
```bash
make run-simulator
```

That's it! Your phone agent should now answer calls and talk with you.

---

### How it works
- **You speak** → agent transcribes and generates a reply
- **Agent speaks back** → using ElevenLabs voice synthesis
- **Conversation continues** → until max turns or timeout

---

### Quick troubleshooting
- **No response**: Check ngrok URL matches in Twilio webhook and config.yaml
- **403 errors**: Verify API_KEY in .env matches expected value
- **Health check**: Run `make health` to verify server is running
- **Clean restart**: Run `make clean` then restart with `make run-dev`

---

## Alternative Manual Setup (Fallback)

If the streamlined approach doesn't work for your system:

### Prerequisites
- **Python 3.10** or higher
- **Twilio** account with phone number
- **ElevenLabs** and **Galtea** API keys

### Manual installation steps

#### Install uv and dependencies:
```bash
# Install uv manually
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone <your_repo_url>
cd Calling-Agent
uv sync
```

#### Install ngrok manually:
```bash
# macOS with Homebrew
brew install ngrok

# Linux/WSL
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok

# Or download from https://ngrok.com/download
```

#### Manual environment setup:
```bash
# Create .env file manually
cat > .env << EOF
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_twilio_auth_token
ELEVENLABS_API_KEY_GAL=your_elevenlabs_api_key
API_KEY=choose_a_simple_password_for_local_use
GALTEA_API_KEY_DEV=your_galtea_api_key
EOF
```

#### Run manually:
```bash
# Terminal 1: Start server
uv run uvicorn agent_twilio:app --host 0.0.0.0 --port 8001 --reload

# Terminal 2: Expose to internet
ngrok http 8001

# Terminal 3: Run simulator
uv run python talk.py
```

### Available make commands
- `make help` - Show all available commands
- `make dev-setup` - Complete automated setup
- `make setup-ngrok` - Install ngrok
- `make run-dev` - Start development server
- `make run-simulator` - Run phone call simulator
- `make health` - Check server health
- `make clean` - Clean temporary files

### Notes
- The current setup uses Spanish for STT/TTS. You can change this in `agent_twilio.py`.
- If your Galtea Test has multiple cases, use `tests: [0,1,2]` in config.yaml.
- When ngrok restarts, update both Twilio webhook and config.yaml with the new URL.
