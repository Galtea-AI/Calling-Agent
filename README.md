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

2.  **Create a virtual environment and install dependencies**:
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

Start the FastAPI server. This will run on `http://localhost:8000`.

```bash
uvicorn twilio_restAPI:app --host 0.0.0.0 --port 8000
```

### 2. Expose the FastAPI Application with ngrok

Twilio requires a publicly accessible URL to send webhooks to. Use ngrok to expose your local FastAPI server.

```bash
ngrok http 8000
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
