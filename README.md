# Twilio Voice with FastAPI and ElevenLabs

This project demonstrates a real-time voice interaction system using Twilio for call management, FastAPI as a backend server, and ElevenLabs for speech-to-text and text-to-speech functionalities. The `experiment.ipynb` notebook provides a way to interact with the system programmatically.

## Features

*   **Real-time Voice Interaction**: Handles incoming Twilio calls and streams audio in real-time.
*   **Speech-to-Text**: Transcribes user speech using ElevenLabs.
*   **Text-to-Speech**: Generates audio responses using ElevenLabs.
*   **Voice Activity Detection (VAD)**: Uses `webrtcvad` to detect speech and silence, optimizing transcription triggers.
*   **Programmatic Interaction**: `experiment.ipynb` allows sending text inputs and receiving transcriptions.

## Project Structure

*   `twilio_restAPI.py`: The main FastAPI application that handles Twilio webhooks, manages WebSocket media streams, and integrates with ElevenLabs.
*   `experiment.ipynb`: A Jupyter Notebook for testing and interacting with the FastAPI application. It includes examples of initiating Twilio calls, sending messages, and receiving transcriptions.
*   `.env`: (Not provided, but assumed) This file should contain your environment variables for Twilio and ElevenLabs API keys, and other configurations.

## Setup and Installation

1.  **Clone the repository**:
    ```bash
    git clone <repository_url>
    cd phone
    ```

2.  **Environment setup (choose one)**:

    - Using Conda (recommended; reproducible via `environment.yml`):
      ```bash
      # Create the env from the provided environment.yml (contains name: phone)
      conda env create -f environment.yml
      conda activate phone
      ```
      - Update the env in place after changes: `conda env update -f environment.yml --prune`
      - List packages in the env: `conda list -n phone`
      - Export the env (without build pins):
        ```bash
        conda env export -n phone --no-builds > environment.yml
        ```

    - Using Python venv and pip:
      ```bash
      python -m venv venv
      source venv/bin/activate  # On Windows, use `venv\\Scripts\\activate`
      pip install -r requirements.txt # Assuming a requirements.txt file exists or create one based on imports
      ```
      *Note*: You'll need to create a `requirements.txt` file manually if it doesn't exist, listing: `fastapi`, `uvicorn`, `python-dotenv`, `twilio`, `elevenlabs`, `webrtcvad`.

3.  **Environment Variables**:
    Create a `.env` file in the root directory of the project with the following variables:
    ```
    TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    TWILIO_AUTH_TOKEN=your_twilio_auth_token
    ELEVENLABS_API_KEY_GAL=your_elevenlabs_api_key
    API_KEY=your_fastapi_app_api_key # This is for securing the /generate endpoint
    ```
    Replace the placeholder values with your actual Twilio and ElevenLabs credentials.

## Usage

### 1. Run the FastAPI Application

Start the FastAPI server. The `run_calling_agent.py` script expects the backend at `http://localhost:8001` (see `BASE_URL`). Either run on port 8001 or adjust that constant.

```bash
uvicorn twilio_restAPI:app --host 0.0.0.0 --port 8001
```

### 2. Expose the FastAPI Application with ngrok

Twilio requires a publicly accessible URL to send webhooks to. Use ngrok to expose your local FastAPI server.

```bash
ngrok http 8001
```
This will provide you with an `https` forwarding URL (e.g., `https://your-ngrok-subdomain.ngrok-free.app`).

### 3. Configure Twilio

You need to configure your Twilio phone number to point to your ngrok URL.

1.  Go to your Twilio Console.
2.  Navigate to "Phone Numbers" -> "Manage" -> "Active numbers".
3.  Select the Twilio phone number you want to use.
4.  Under the "Voice & Fax" section, in the "A CALL COMES IN" part, set the "CONFIGURE WITH" dropdown to "Webhook".
5.  Set the URL to your ngrok forwarding URL appended with `/twilio-voice` (e.g., `https://your-ngrok-subdomain.ngrok-free.app/twilio-voice`).
6.  Ensure the HTTP method is set to `POST`.
7.  Save your changes.

### 4. Use the `experiment.ipynb` Notebook

Open `experiment.ipynb` in a Jupyter environment.

1.  **Initiate a Call**: The first cell of the notebook contains code to initiate a call from your Twilio number to a specified `to` number. Update the `from_` and `to` numbers as needed, and ensure the `url` matches your current ngrok forwarding URL.
    ```python
    call = client.calls.create(
        from_="+12136957366", # Your Twilio phone number
        to="+34960324442",     # The recipient's phone number
        url="https://69b8bda2c963.ngrok-free.app/twilio-voice", # Your ngrok URL
    )
    ```
2.  **Interact with the `/generate` endpoint**: The notebook then demonstrates how to make requests to the `/generate` endpoint of your FastAPI application.
    *   The `first=True` parameter is used for the initial call to get the first transcription from the user.
    *   Subsequent calls use `first=False` and include an `input` parameter, which represents the text response you want your AI to speak.
    *   **Note**: The notebook currently uses fixed input strings for these subsequent calls. You would integrate your AI logic here to generate dynamic responses based on the user's transcription.

### Important Notes

*   **Fixed Inputs**: Currently, the `experiment.ipynb` uses hardcoded input strings for the AI's responses. To build a dynamic conversation, you would replace these fixed inputs with your own AI logic that generates responses based on the received transcriptions.
*   **API Key**: The `/generate` endpoint in `twilio_restAPI.py` is secured with an `X-API-KEY` header, which is read from your `.env` file. Ensure this is correctly set up.
*   **ElevenLabs Configuration**: The `twilio_restAPI.py` file uses specific `voice_id`, `output_format`, `model_id`, and `language_code` for ElevenLabs. Adjust these as necessary for your desired voice and language.
*   **VAD Tuning**: The `SILENCE_CHUNKS_TRIGGER` in `twilio_restAPI.py` (default 140) determines how long silence needs to be detected before a speech segment is considered complete. You might need to tune this value based on your audio and conversation flow.

## Troubleshooting

*   **Ngrok URL**: Ensure your ngrok URL is up-to-date in both your Twilio phone number configuration and the `experiment.ipynb` file. Ngrok free accounts generate new URLs each time they are started.
*   **Environment Variables**: Double-check that all environment variables in your `.env` file are correctly set and loaded.
*   **FastAPI Logs**: Monitor your FastAPI console for any errors or unexpected behavior.
*   **Twilio Debugger**: Use the Twilio Debugger in your Twilio Console to check for any issues with webhooks or media streams.

## Run the calling agent (Galtea simulator)

With the FastAPI app running and exposed via ngrok, you can execute the agent-driven simulation which places a Twilio call and alternates turns using the `/generate` endpoint.

```bash
python run_calling_agent.py
```

## Inputs and configuration used by `run_calling_agent.py`

`run_calling_agent.py` defines a `MyAgent` that controls the phone call and interacts with your FastAPI server.

- Constructor inputs for `MyAgent(remote_url, from_number, to_number)`:
  - `remote_url`: Your public HTTPS URL (e.g., ngrok) where Twilio will POST `/twilio-voice`.
  - `from_number`: Your Twilio number in E.164 format (e.g., `+12135551234`).
  - `to_number`: Destination number in E.164 format.

- Environment variables used:
  - `TWILIO_ACCOUNT_SID`: Twilio Account SID.
  - `TWILIO_AUTH_TOKEN`: Twilio Auth Token.
  - `API_KEY`: API key sent as `X-API-KEY` header to the FastAPI `/generate` endpoint.
  - `GALTEA_API_KEY_DEV`: API key for the Galtea SDK.

- Backend endpoint referenced by the agent:
  - `BASE_URL`: `http://localhost:8001` (adjust if you run the API elsewhere/port).
  - `GET /generate`: Parameters used by the agent:
    - `first` (bool): If true, waits for first user transcription; if false, sends agent input and waits for next transcription.
    - `timeout` (float, seconds): Max time to wait before 204 No Content.
    - `input` (str): Agent text to be synthesized and played to the user.

- Galtea simulation settings used in the script:
  - `test_id`, `version_id`: Used to select test cases and session version.
  - `test_case_num`: Local indices of test cases to run.
  - `max_turns`, `agent_goes_first`: Control conversation length and starter.

Tip: Ensure your FastAPI app's `X-API-KEY` check matches the `API_KEY` you provide in `.env`, and that your Twilio phone number webhook points to `<remote_url>/twilio-voice`.
