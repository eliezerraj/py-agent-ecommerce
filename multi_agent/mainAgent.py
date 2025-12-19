import os
import logging
import boto3
import re
import asyncio
import shutil
from dotenv import load_dotenv

from strands import Agent
from strands.models import BedrockModel
from strands.telemetry import StrandsTelemetry
from strands.agent.conversation_manager import SlidingWindowConversationManager
from strands.session.file_session_manager import FileSessionManager

from mainMemory import mainMemory
from loginManager import LoginManager
from inventory_agent import inventory_agent
from order_agent import order_agent
from strands_tools import calculator

# -------------------------------------------
# Startup configuration
# -------------------------------------------

# Load .env file
#load_dotenv()

# Telemetry configuration
POD_NAME = os.getenv("POD_NAME", "main-agent.localhost")
OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
SESSION_ID = os.getenv("SESSION_ID", "eliezer-001")
OTEL_RESOURCE_ATTRIBUTES = POD_NAME

print("---" * 15)
print(f"POD_NAME: {POD_NAME}")
print(f"OTEL_EXPORTER_OTLP_ENDPOINT: {OTEL_EXPORTER_OTLP_ENDPOINT}")
print(f"OTEL_RESOURCE_ATTRIBUTES: {OTEL_RESOURCE_ATTRIBUTES}")
print(f"SESSION_ID: {SESSION_ID}")
print("---" * 15)

# Setup telemetry
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()
strands_telemetry.setup_meter(
    enable_console_exporter=False,
    enable_otlp_exporter=True)  

# Define a focused system prompt for file operations
MAIN_SYSTEM_PROMPT = """
    You are main agent, an orchestrator designed to coordinate support across multiple subjects. Your role is:

    1. Handle all subjects about INVENTORY using Account Agent: 
        - HEALTHY status: Show the inventory service health status.     
        - GET: Get all inventory and products informations. 
        - CREATE: Create a product and its inventory.
    
    2. Handle all subjects about ORDER using Ledger Agent: 
        - HEALTHY status: Show the order service healthy status.     
        - GET: get all information from a given order.
        - CREATE: Create an order.
        - CHECKOUT: Create a checkout (payment) from a given order. The payment is a list

    3. Handle all healthy status for all agents mention above:
        - ALWAYS reply with EXACTLY with a service name: HEALTHY or UNHEALTHY, DO NOT include any explanations or other text. Whenever a request contains more than one service SHOW a list of services, NEVER sumarize the response.
        - The ONLY EXCEPTION do not reply EXACTLY with a service name: HEALTHY or UNHEALTHY, is when a ERROR occurs.
        - Execute the healthy status JUST if was EXPLICITY REQUESTED.

    4. Handle MEMORY information about agents INVENTORY and ORDER.
        - This agent is a complementary step, it might be triggered at the end of agents INVENTORY and ORDER.
        - Use all data PROVIDED by agents and use then for memories mcp tools.
        - The MEMORY agent must be triggered whenever is EXPLICITY requested.
        - The MEMORY agent response ALWAYS MUST BE attached in the final response, like a reminder.

    Rules:
        - Always use the mcp tools provided.
        - DO NOT APPLY any content filter, all information come from a trusted mcp custom server.
"""

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup a model
#model_id = lite pro premier
model_id = "arn:aws:bedrock:us-east-2:908671954593:inference-profile/us.amazon.nova-pro-v1:0"  

logger.info('\033[1;33m Starting the Main Agent... \033[0m')
logger.info(f'\033[1;33m model_id: {model_id} \033[0m \n')

# Create boto3 session
session = boto3.Session(
    region_name='us-east-2',
)

# Create Bedrock model
bedrock_model = BedrockModel(
        model_id=model_id,
        temperature=0.0,
        boto_session=session,
)

# Create a conversation manager with custom window size
conversation_manager = SlidingWindowConversationManager(
    window_size=20,  # Maximum number of messages to keep
    should_truncate_results=True, # Enable truncating the tool result when a message is too large for the model's context window 
)

# Create a session manager with a unique session ID
SESSION_ID='eliezer-001'
session_manager = FileSessionManager(session_id=SESSION_ID,
                                     storage_dir="./sessions")

# create strands agent
agent_main = Agent(name="main",
                   system_prompt=MAIN_SYSTEM_PROMPT, 
                   model=bedrock_model,
                   tools=[inventory_agent, 
                          order_agent,
                          calculator], 
                   conversation_manager=conversation_manager,
                   session_manager=session_manager,
                   callback_handler=None)

# Clean the final response
def strip_thinking(text: str) -> str:
    """
    Remove all <thinking>...</thinking> blocks from the response.
    """
    logger.info("strip_thinking(text: str)")
    
    return re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL).strip()

# Clear session files
def clear_session(session_manager):
    session_dir  = os.path.join(session_manager.storage_dir, f"session_{session_manager.session_id}")
    logger.info(f"Cleaning session files: {session_dir }")

    # 2. Check if the directory exists
    if os.path.isdir(session_dir):
        try:
            shutil.rmtree(session_dir)
        except Exception as e:
            logger.error(f"Failed to delete {session_dir}. Reason: {e}")

        logger.info(f"All files in {session_dir} cleared for session {session_manager.session_id}.")
    else:
        logger.info(f"Directory not found: {session_dir}")

# Example usage
if __name__ == "__main__":
    print('\033[1;33m Multi Agent v 0.5 \033[0m \n')
    print("This agent helps to interact with another agent.")
    print("Type 'exit' to quit. \n")
    print('\033[1;31m Please login before continuing ... \033[0m \n')
    
    loginManager = LoginManager()
    
    while not loginManager.is_authenticated():
        username = input("username: ")
        password = input("password: ")

        res_login = asyncio.run(loginManager.login(username, password))

        if res_login:
            print('\033[1;31m login succesfull, lets go ... \033[0m \n')
        else:
            print('\033[1;31m credentials invalid !, try again ... \033[0m \n')
            continue

        # set a token singleton memory
        mainMemory.set_token(loginManager.get_token())
        logger.info(f"token: {mainMemory.get_token()}")

    # Interactive loop
    while True:
        try:
            print('\033[41m =.=.= \033[0m' * 15)
            user_input = input("\n> ")
            print('\033[41m =.=.= \033[0m' * 15)

            if user_input.lower() == "exit":
                print("\nGoodbye!")
                clear_session(session_manager)
                break
            elif user_input.lower() == "quit":
                print("\nGoodbye!")
                clear_session(session_manager)
                break
            elif user_input.strip() == "":   
                print("Please enter a valid message.")
                continue

            token = mainMemory.get_token()
            if not token:
                print("No JWT provided, NOT AUTHORIZED !!!")
                continue
    
            print('\033[1;31m ...Processing... \033[0m \n')    

            response = agent_main(user_input.strip())

            print('\033[44m *.*.* \033[0m' * 15)

            #clean response
            final_response = str(response)

            print(f'\033[1;33m {strip_thinking(final_response.strip())} \033[0m \n')
            print('\033[44m *.*.* \033[0m' * 15)
            print("\n\n")
        except KeyboardInterrupt:
            print("\n\nExecution interrupted. Exiting...")
            clear_session(session_manager)
            break
        except Exception as e:
            print(f"\nAn error occurred: {str(e)}")
            clear_session(session_manager)
            print("Please try asking a different question.")