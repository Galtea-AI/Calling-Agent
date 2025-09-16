import asyncio
import base64
import json
import os, wave, io
import signal
import time
import functools
import audioop
import webrtcvad
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import Response
import elevenlabs
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv
from fastapi import HTTPException, Depends
from elevenlabs import VoiceSettings
from starlette.websockets import WebSocketDisconnect
from twilio.rest import Client

app = FastAPI()
load_dotenv()

async def verify_api_key(request: Request):
    """
    A dependency to verify the X-API-KEY header.
    """
    api_key = request.headers.get("x-api-key")
    if not api_key or api_key != app.state.SECRET_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid or missing API Key."
        )

    
def reset_app_state():
    """Resets the global application state to its default values for a new call."""
    app.state.active = "agent"  # agent or user
    app.state.transcription = None
    app.state.transcription_event = asyncio.Event()
    app.state.input = None
    app.state.input_event = asyncio.Event()
    app.state.first_ = True
    app.state.mark_found = False
    app.state.time_since_last_talk = time.time()
    app.state.SHUTDOWN_EVENT = asyncio.Event()
    app.state.sid = None

@app.on_event("startup")
async def startup():
    """Initializes global constants and sets the initial state."""
    app.state.SAMPLE_RATE = 8000
    app.state.SILENCE_CHUNKS_TRIGGER = 140
    app.state.SECRET_KEY = os.getenv("API_KEY")
    app.state.talk_timeout = 50.0
    app.state.account_sid = os.environ["TWILIO_ACCOUNT_SID"]
    app.state.auth_token = os.environ["TWILIO_AUTH_TOKEN"]
    app.state.client = Client(app.state.account_sid, app.state.auth_token)


def signal_handler():
    if not app.state.SHUTDOWN_EVENT.is_set():
        app.state.SHUTDOWN_EVENT.set()
        print("Signal handler called")


@app.post("/twilio-voice")
async def twilio_voice(request: Request):
    """
    Receives the initial call event from Twilio and responds with TwiML
    to start a media stream.
    """
    twiml = (
        '<Response>'
        '<Connect>'
        f'<Stream url="wss://{request.url.hostname}/media"/>'
        '</Connect>'
        '</Response>'
    )
    print("Received call webhook, responding with TwiML to start stream.")
    return Response(content=twiml, media_type="application/xml")


# WebSocket endpoint to handle real-time audio
@app.websocket("/media")
async def media_stream(ws: WebSocket):
    """
    Starts the async thread which will recieve the audio from 
    twilio through the websocket.
    """
    await ws.accept()
    stream_sid = None
    print("WebSocket connection established with Twilio")
    audio_buffer = bytearray()
    api_key_gal = os.getenv("ELEVENLABS_API_KEY_GAL")
    elevenlabs_client = ElevenLabs(api_key=api_key_gal)
    user_response = ""
    timeout = 50.0

    async def receive_from_twilio():
        """
        Recieves the audio from twilio through the websocket
        """
        nonlocal stream_sid, audio_buffer, elevenlabs_client
        vad = webrtcvad.Vad()
        vad.set_mode(3)  # 3 is most aggressive
        silence_counter = 0
        speech_detected = False
        current_state = None  # To print state changes only once

        async for raw_msg in ws.iter_text():
            
            msg = json.loads(raw_msg)
            evt = msg["event"]  # start, media, stop, mark 
            time_since_last_talk = time.time() - app.state.time_since_last_talk
            if evt == "stop" or (time_since_last_talk >= app.state.talk_timeout) or app.state.SHUTDOWN_EVENT.is_set():
                signal_handler()
                app.state.transcription = "Conversation ended by Twilio"
                app.state.transcription_event.set()
                if time_since_last_talk >= app.state.talk_timeout:
                    print("Stream stopped by the talk timeout and ws closed",msg)
                    await ws.close()
                app.state.client.calls(f"{app.state.sid}").update(status='completed')
                print("Stream stopped by Twilio",time_since_last_talk)

            elif app.state.active == "agent" and ( app.state.first_ or evt == "mark" or app.state.mark_found ):

                if evt == "mark":
                    mark = msg.get("mark", {}).get("name")
                    if mark == "endOfPlayback":
                        app.state.mark_found = True
                if evt == "start":
                    stream_sid = msg["start"]["streamSid"]
                    print(f"Stream started: {stream_sid}")
                elif evt == "media":
                    audio_b64 = msg["media"]["payload"]
                    audio_bytes = base64.b64decode(audio_b64)
                    presentation_timestamp = msg["media"]["timestamp"]
                    time_since_start_sec = float(presentation_timestamp) / 1000.0

                    # Twilio sends u-law audio, VAD needs linear PCM
                    pcm_audio = audioop.ulaw2lin(audio_bytes, 2)

                    try:
                        is_speech = vad.is_speech(pcm_audio, sample_rate=app.state.SAMPLE_RATE)

                        if is_speech:
                            if current_state != "speech":
                                print(f"[{time_since_start_sec:.2f}s] Speech detected.")
                                current_state = "speech"
                            speech_detected = True
                            silence_counter = 0
                            # Append audio only when speech is detected
                            audio_buffer.extend(pcm_audio)
                        
                        elif speech_detected: # This is a silence chunk immediately following speech
                            
                            if current_state != "silence":
                                print(f"[{time_since_start_sec:.2f}s] Silence detected.")
                                current_state = "silence"
                            silence_counter += 1
                            audio_buffer.extend(pcm_audio) # to include silence in the buffer for sinding to ElevenLabs.
                            # Trigger AI after a sufficient period of silence 
                            if silence_counter >= app.state.SILENCE_CHUNKS_TRIGGER:

                                print(f"[{time_since_start_sec:.2f}s] --- End of speech detected! Triggering S2T. ---")
                                # Note: The audio_buffer is 8kHz, 16-bit PCM.
                                if audio_buffer:
                                    # timestamp = int(time.time())
                                    # filename = os.path.join('./', f"recording_{timestamp}.wav")
                                    try:
                                        # with wave.open(filename, 'wb') as wf:
                                        #     wf.setnchannels(1)  # Mono audio
                                        #     wf.setsampwidth(2)  # 16-bit samples (2 bytes)
                                        #     wf.setframerate(SAMPLE_RATE) # 8000 Hz
                                        #     wf.writeframes(bytes(audio_buffer))
                                        with io.BytesIO() as wav_buffer:
                                            with wave.open(wav_buffer, 'wb') as wf:
                                                wf.setnchannels(1)
                                                wf.setsampwidth(2)
                                                wf.setframerate(app.state.SAMPLE_RATE)
                                                wf.writeframes(bytes(audio_buffer))
                                            audio_data = wav_buffer.getvalue()
                                    except Exception as e:
                                        print(f"Error saving WAV file to buffer: {e}")
                                    try:
                                        print(f"Sending {len(audio_buffer)} bytes to ElevenLabs.")
                                        
                                        transcription = elevenlabs_client.speech_to_text.convert(
                                            file=audio_data, 
                                            model_id="scribe_v1",
                                            language_code="es",
                                        )
                                        print("Agent:", transcription.text)
                                        if app.state.active == "agent":
                                            
                                            app.state.transcription =  transcription.text
                                            app.state.transcription_event.set() 
                                            
                                        
                                    except Exception as e:
                                        print(f"Error calling ElevenLabs: {e}")
                                    
                                        
                                
                                # Reset state for the next utterance
                                speech_detected = False
                                silence_counter = 0
                                current_state = None
                                audio_buffer.clear()

                    except Exception as e:
                        print(f"Error processing VAD: {e}")

            


    async def send_to_twilio():
        """Handles outbound messages to Twilio's media stream."""
        nonlocal stream_sid, user_response, timeout, elevenlabs_client

        # Wait until the stop flag is set to True
        while not app.state.SHUTDOWN_EVENT.is_set():
            if app.state.active == "user":
                
                await asyncio.wait_for(app.state.input_event.wait(), timeout=timeout)
                app.state.input_event = asyncio.Event()
                user_response = app.state.input

                response = elevenlabs_client.text_to_speech.convert(
                    voice_id="5IDdqnXnlsZ1FCxoOFYg",  output_format="pcm_8000", text=user_response,  model_id="eleven_flash_v2_5",language_code="es" ,
                    voice_settings=VoiceSettings( stability=0.0, similarity_boost=1.0, style=1.0, use_speaker_boost=True, speed=1.0, ), )
                audio_buffer_response = b''
                CHUNK_BYTES = 8000
                audio_buffers = b''
                for chunk in response:
                    if chunk:
                        audio_buffers += chunk
                        while len(audio_buffers) >= CHUNK_BYTES:
                            current_chunk = audio_buffers[:CHUNK_BYTES]
                            audio_buffers = audio_buffers[CHUNK_BYTES:]
                            # model.feed_audio(current_chunk)
                            audio_buffer_response+=current_chunk
                            # time.sleep(0.25)
                if audio_buffers:
                    audio_buffer_response+=audio_buffers
                mulaw_bytes = audioop.lin2ulaw(audio_buffer_response, 2)  # width=2 for 16-bit PCM
                b64_payload = base64.b64encode(mulaw_bytes).decode('ascii') 
                
                audio_delta = {
                    "event": "media",
                    "streamSid": stream_sid,
                    "media": {
                        "payload": b64_payload
                    }
                }
                try:
                    await ws.send_json(audio_delta)
                except (WebSocketDisconnect, RuntimeError) as e:
                    print(f"Send failed (media). Assuming websocket closed: {e}")
                    signal_handler()
                    break
                
                # after this send a mark to the twilio to show that the audio has sopped playing at client side
                try:
                    await ws.send_json({
                        "event": "mark",
                        "streamSid": stream_sid,
                        "mark": {
                            "name": "endOfPlayback"
                        }
                        })
                except (WebSocketDisconnect, RuntimeError) as e:
                    print(f"Send failed (mark). Assuming websocket closed: {e}")
                    signal_handler()
                    break
                print(f"User: {user_response}")
                app.state.active = "agent"
                
            await asyncio.sleep(0.2)


    try:
        loop = asyncio.get_running_loop()

        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, signal_handler)

        await asyncio.gather(receive_from_twilio(), send_to_twilio())
    except Exception as e:
        print(f"WebSocket error: {e}")
            

@app.get("/generate", dependencies=[Depends(verify_api_key)] )
async def get_latest(client, sid, first: bool = False, timeout: float | None = 30.0, input: str = "", talk_timeout: float | None = 80.0):
    app.state.time_since_last_talk = time.time()
    if first:
        try:
            reset_app_state()
            app.state.talk_timeout = talk_timeout
            app.state.sid = sid
            await asyncio.wait_for(app.state.transcription_event.wait(), timeout=timeout)
            app.state.transcription_event = asyncio.Event()
            response = {"response": app.state.transcription}
            app.state.active = "user"
            app.state.first_ = False
            # app.state.mark_found = False
            return response
        except asyncio.TimeoutError:
            raise HTTPException(status_code=204, detail="No new value")
    else:
        app.state.input = input
        app.state.input_event.set()
        
        try:
            await asyncio.wait_for(app.state.transcription_event.wait(), timeout=timeout)
            app.state.transcription_event = asyncio.Event()
            response = {"response": app.state.transcription}
            app.state.active = "user"
            app.state.mark_found = False
            return response
        except asyncio.TimeoutError:
            raise HTTPException(status_code=204, detail="No new value")


