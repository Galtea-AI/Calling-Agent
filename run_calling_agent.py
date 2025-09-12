import galtea
import requests
import json
from dotenv import load_dotenv
from twilio.rest import Client
from galtea import Galtea
import os,uuid,time

load_dotenv()

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

    def start_call(self):
        
        self.call_twilio = self.client.calls.create(
            from_=self.from_number,
            to=self.to_number,
            url=f"{self.remote_url}/twilio-voice",
        )
        print(f"Call started with sid: {self.call_twilio.sid}")

    def end_call(self):
        self.client.calls(f"{self.call_twilio.sid}").update(status='completed')

    def generate_(self,first, timeout, input):
        params_first_call = { "first": first,  "timeout": timeout, "input": input }
        try:
            response_first = requests.get( f"{self.BASE_URL}/generate",  headers=self.headers, params=params_first_call )
            if response_first.status_code == 200:
                print("Response JSON:", response_first.json())
                return response_first.json()
            elif response_first.status_code == 204:
                print("Response: No content (Timeout reached, no user speech detected).")
            else:
                print("Error Response:", response_first.text)
        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")


    def call(self, input_data: galtea.AgentInput) -> galtea.AgentResponse:

        if len(input_data.messages) ==0:
            self.start_call()
            print("call started")
            response = self.generate_(True, 30.0, "")
            print("response generated")
        else:
            print("generating response with user message")
            user_message = input_data.last_user_message_str()
            print("generating response with user message1")

            response = self.generate_(False, 30.0, user_message)
            print("generating response with user message2")


        return galtea.AgentResponse( content=response["response"],  metadata={"model_version": "1.0"} )




api_key = os.environ["GALTEA_API_KEY_DEV"]
galtea_client = Galtea(api_key=api_key)
test_cases = galtea_client.test_cases.list(test_id="mayfgsdeqpc076x36l5ckymz")
test_case_num = [1,2]


results = []
for i, test_case in enumerate(test_cases):
    if i in test_case_num:

        time.sleep(2)
        # +34960324442
        agent = MyAgent(remote_url="https://kosh6r5673fg71.ngrok-free.app",
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

        