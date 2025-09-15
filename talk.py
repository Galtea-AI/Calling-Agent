import galtea
import requests
import json
import signal
from dotenv import load_dotenv
from twilio.rest import Client
from galtea import Galtea
import os,uuid,time

load_dotenv()
sid = None

class MyAgent(galtea.Agent):
    def __init__(self,remote_url,from_number,to_number):
        account_sid = os.environ["TWILIO_ACCOUNT_SID"]
        auth_token = os.environ["TWILIO_AUTH_TOKEN"]
        self.client = Client(account_sid, auth_token)
        API_KEY = os.environ["API_KEY"] 
        self.BASE_URL = "http://localhost:8001"
        self.headers = { "x-api-key": API_KEY, "Content-Type": "application/json" }
        self.remote_url = remote_url
        self.from_number = from_number
        self.to_number = to_number
        self.asycio_timeout = 120.0
        self.request_timeout = 120.0
        self.sid = None
        self.conversation_ended = False

    def start_call(self):
        
        self.call_twilio = self.client.calls.create(
            from_=self.from_number,
            to=self.to_number,
            url=f"{self.remote_url}/twilio-voice",
        )
        print(f"Call started with sid: {self.call_twilio.sid}")
        global sid
        sid = self.call_twilio.sid

    def end_call(self):
        self.client.calls(f"{self.call_twilio.sid}").update(status='completed')

    def generate_(self,first, timeout, input):
        params_first_call = {"client":self.client, "sid": self.call_twilio.sid, "first": first,  "timeout": timeout, "input": input, "talk_timeout": 80 }
        try:
            response_first = requests.get( f"{self.BASE_URL}/generate",  headers=self.headers, params=params_first_call, timeout=self.request_timeout )
            if response_first.status_code == 200:
                print("Response JSON:", response_first.json())
                return response_first.json()
            elif response_first.status_code == 204:
                print("Response: No content (Timeout reached, no user speech detected). Exiting main script.")
                exit(0)
            else:
                print("Error Response:", response_first.text)
                print("Exiting main script.")
                exit(0)

        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")
            print("Exiting main script.")
            exit(0)

    def call(self, input_data: galtea.AgentInput) -> galtea.AgentResponse:

        if len(input_data.messages) ==0:
            self.start_call()
            print("call started")
            response = self.generate_(True, self.asycio_timeout, "")
            print("response generated")
        else:
            if not self.conversation_ended:
                print("generating response with user message")
                user_message = input_data.last_user_message_str()
                response = self.generate_(False, self.asycio_timeout, user_message)
                if response["response"] == "Conversation ended by Twilio":
                    self.conversation_ended = True
            else:
                response = {}
                response["response"] = "Conversation ended by Twilio"

        return galtea.AgentResponse( content=response["response"],  metadata={"model_version": "1.0"} )


def shutdown_handler(signum, frame):
    """
    This function is our custom signal handler.
    It will be executed when this script receives SIGINT or SIGTERM.
    """
    print(f"\nCaught signal {signum}. Initiating graceful shutdown...")
    if sid:
        account_sid = os.environ["TWILIO_ACCOUNT_SID"]
        auth_token = os.environ["TWILIO_AUTH_TOKEN"]
        client = Client(account_sid, auth_token)
        client.calls(f"{agent.call_twilio.sid}").update(status='completed')
        print(" Twilio call status updated to completed")
    print("Exiting main script.")
    exit(0)

for sig in (signal.SIGTERM, signal.SIGINT):
    signal.signal(sig, shutdown_handler)



api_key = os.environ["GALTEA_API_KEY_DEV"]
galtea_client = Galtea(api_key=api_key)
test_cases = galtea_client.test_cases.list(test_id="mayfgsdeqpc076x36l5ckymz")
test_case_num = [1,2]


results = []
for i, test_case in enumerate(test_cases):
    if i in test_case_num:

        time.sleep(2)
        # +34960324442
        agent = MyAgent(remote_url="https://d132dd45a2cd.ngrok-free.app",
        from_number="+12136957366",to_number="+34960324442")
        uid = str(uuid.uuid4())

        


        # Create a session for this test case
        session = galtea_client.sessions.create(
            version_id="hwtq29i0jrhosqpukiobu6n4",
            test_case_id=test_case.id,
            custom_id=f"Phone{uid}" # got stuck on Blocking1
        )

        # Run the simulation
        result = galtea_client.simulator.simulate(
            session_id=session.id,
            agent=agent,
            max_turns=12,
            agent_goes_first=True
        )
        print("call ended")

        agent.end_call()
        results.append(result)

        # Review results
        print(f"Completed {result.total_turns} turns. Finished: {result.finished}")
        if result.stopping_reason:
            print(f"Stopping reason: {result.stopping_reason}")
        print(f"passed one thing_, {i}")
        # break 

        