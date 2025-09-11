# File: main.py (FastAPI app)

from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import Response
import asyncio
import base64
import json, time 

app = FastAPI()

# Endpoint to return TwiML and initiate a bidirectional stream
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
    Handles the WebSocket connection for real-time audio streaming.
    Receives audio from Twilio and sends audio back.
    """
    await ws.accept()
    stream_sid = None
    print("WebSocket connection established with Twilio")

    # The Twilio stream can sometimes send a large amount of data
    # This buffer can help manage the flow.
    audio_buffer = bytearray()
    wav_written = False  # Initialize here to persist across the connection

    import webrtcvad
    import audioop

    async def receive_from_twilio():
            nonlocal stream_sid, audio_buffer, wav_written

            # --- VAD Initialization ---
            vad = webrtcvad.Vad()
            vad.set_mode(3)

            SAMPLE_RATE = 8000
            
            # --- End of Speech Detection Logic ---
            # How long of a silence period to wait for before triggering the AI.
            # Twilio sends 20ms chunks, so 100 chunks is 2000ms of silence.
            SILENCE_CHUNKS_TRIGGER = 115
            
            silence_counter = 0
            speech_detected = False
            
            # Track the current state to print only on change
            current_state = None

            async for raw_msg in ws.iter_text():
                msg = json.loads(raw_msg)
                evt = msg.get("event")

                if evt == "start":
                    stream_sid = msg["start"]["streamSid"]
                    print(f"Stream started: {stream_sid}")

                elif evt == "media":
                    audio_b64 = msg["media"]["payload"]
                    audio_bytes = base64.b64decode(audio_b64)
                    presentation_timestamp = msg["media"]["timestamp"]
                    time_since_start_sec = float(presentation_timestamp) / 1000.0
                    
                    pcm_audio = audioop.ulaw2lin(audio_bytes, 2)

                    try:
                        is_speech = vad.is_speech(pcm_audio, sample_rate=SAMPLE_RATE)

                        if is_speech:
                            # If we were previously silent or in the initial state, print "Speech detected"
                            if current_state != "speech":
                                print(f"[{time_since_start_sec:.2f}s] Speech detected.")
                                current_state = "speech"
                            
                            speech_detected = True
                            silence_counter = 0
                                
                        else: # Silence is detected
                            # If speech was previously detected, start counting silence
                            if speech_detected:
                                # If we were previously speaking, print "Silence detected"
                                if current_state != "silence":
                                    print(f"[{time_since_start_sec:.2f}s] Silence detected.")
                                    current_state = "silence"
                                
                                silence_counter += 1

                        # If enough silent chunks have passed after speech, trigger the end of speech
                        if silence_counter >= SILENCE_CHUNKS_TRIGGER:
                            print(f"[{time_since_start_sec:.2f}s] --- End of speech detected! Triggering AI. ---")
                            # ---------------------------------------------
                            # YOUR CODE TO TRIGGER YOUR AI GOES HERE
                            # ---------------------------------------------
                            
                            # Reset the state for the next utterance
                            speech_detected = False
                            silence_counter = 0
                            current_state = None # Reset state

                    except Exception as e:
                        print(f"Error processing VAD: {e}")

                    audio_buffer.extend(audio_bytes)

                elif evt == "stop":
                    print("Stream stopped by Twilio")
                    break
    async def send_to_twilio():
        import random

        nonlocal stream_sid
        # Wait until we have the streamSid from the 'start' event
        while not stream_sid:
            await asyncio.sleep(0.1)

        # Generate 1 second of random 8-bit u-law audio (8000 samples)
        # u-law bytes range from 0x00 to 0xFF, so random bytes are fine for noise
        random_bytes = bytes(random.getrandbits(8) for _ in range(8000))
        payload = base64.b64encode(random_bytes).decode('ascii')

        # await ws.send_text(json.dumps({
        #     "event": "media",
        #     "streamSid": stream_sid,
        #     "media": {"payload": payload}
        # }))
        # print("Sent random outbound audio to Twilio")

        # Optionally, send a mark to get a confirmation when Twilio finishes playing
        # await ws.send_text(json.dumps({
        #     "event": "mark",
        #     "streamSid": stream_sid,
        #     "mark": {"name": "greeting_done"}
        # }))

    try:
        # Run both tasks concurrently
        await asyncio.gather(receive_from_twilio(), send_to_twilio())
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await ws.close()
        print("WebSocket closed")