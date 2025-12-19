import logging
import boto3
import time
import json

from mainMemory import mainMemory

from opentelemetry import trace, metrics, propagate

from mcp.client.streamable_http import streamablehttp_client

from strands import Agent, tool
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from strands.hooks import (HookProvider, 
                           HookRegistry, 
                           AfterInvocationEvent, 
                           AfterToolCallEvent, 
                           BeforeInvocationEvent, 
                           BeforeToolCallEvent
)

INVENTORY_SYSTEM_PROMPT = """
    You are INVENTORY agent specialized to handle all informations about INVENTORY and PRODUCTS.

    Inventory Operations:

        1. inventory_healthy: check the healthy status INVENTORY service.       
            - response:
                - content: all information about INVENTORY service health status and enviroment variables. 
            inventory_healthy rule:
                - This tool must be triggered ONLY with a EXPLICITY requested.
                - return only the status code, consider 200 as healthy, otherwise unhealthy.

        1. get_product: get products details such as sku, name, type, status (IN-STOCK, OUT-OF-STOCK), date of creation (created_at) from a given product(sku)
            - args: 
                - product: sku of product.
            - response: 
                - product details such as sku, name, type, status (IN-STOCK, OUT-OF-STOCK), date of creation (created_at).
        
        2. get_inventory: get all product inventory information such as available quantity, reserver quantity and sold quantity.
            - args: 
                - product: sku.
            - reponse: 
                - inventory: All inventory information for a product.
        
        4. create_inventory: Create a product and its inventory.
            - args: 
                - product: sku, name, type and status.
            - response: 
                - product: all product details such sku, name, type and status, date of creation (created_at).       

    Definitions and Rules:
        - Always use the mcp tools provided.
        - USE EXACTLY the fields provided by query, DO NOT PARSE, DO NOT STRIP OF '.' or '-' or FORMAT.
        - USE EXACTLY the fields names provided by json response. eg: sku, product_id, etc.
        - DO NOT UPDATE any field format provided by mcp tool, use EXACTLY the mcp field result format.
"""

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup a model
#model_id = lite pro premier
model_id = "arn:aws:bedrock:us-east-2:908671954593:inference-profile/us.amazon.nova-pro-v1:0"  

logger.info('\033[1;33m Starting the Inventory Agent... \033[0m')
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

# load mcp servers
mcp_url = "http://127.0.0.1:9002/mcp"

#Create mcp_server_client
headers = {}
def create_streamable_http_mcp_server(mcp_url: str):    
    propagate.inject(headers)
    return streamablehttp_client(mcp_url, headers=headers)

streamable_http_mcp_server = MCPClient(lambda: create_streamable_http_mcp_server(mcp_url))

class ToolValidationError(Exception):
    """Custom exception to abort tool calls immediately."""
    pass

# Agent hook setup
class AgentHook(HookProvider):

    def __init__(self):
        self.start_agent = ""
        self.tool_name = "unknown"
        self.metrics = {}

    # Register hooks
    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeInvocationEvent, self.agent_start)
        registry.add_callback(AfterInvocationEvent, self.agent_end)
        registry.add_callback(BeforeToolCallEvent, self.before_tool)
        registry.add_callback(AfterToolCallEvent, self.after_tool)

    # Hook implementations start (get time, log tool usage, collect metrics, etc.)
    def agent_start(self, event: BeforeInvocationEvent) -> None:
        logger.info(f" *** BeforeInvocationEvent **** ")
        self.start_agent = time.time()
        logger.info(f"Request started - Agent: {event.agent.name} : { self.start_agent }")

    # Hook implementations end (get time, log tool usage, collect metrics, etc.)
    def agent_end(self, event: AfterInvocationEvent) -> None:
        logger.info(f" *** AfterInvocationEvent **** ")

        duration = time.time() - self.start_agent

        logger.info(f"Request completed - Agent: {event.agent.name} - Duration: {duration:.2f}s")
        
        self.metrics["total_requests"] = self.metrics.get("total_requests", 0) + 1
        self.metrics["avg_duration"] = (
            self.metrics.get("avg_duration", 0) * 0.9 + duration * 0.1 # Exponencial Moving Average 
        )

        logger.info(f" *** *** self.metrics *** *** ")
        logger.info(f" {self.metrics}")
        logger.info(f" *** *** self.metrics *** *** ")

    def before_tool(self, event: BeforeToolCallEvent) -> None:
        logger.info(f"*** Tool invocation - agent: {event.agent.name} : { event.tool_use.get('name') } *** ")

    def after_tool(self, event: AfterToolCallEvent) -> None:
        logger.info(f" *** AfterToolCallEvent **** ")
        
        self.tool_name = event.tool_use.get("name")
        logger.info(f"* Tool completed - agent: {event.agent.name} : {self.tool_name}")

@tool
def inventory_agent(query: str) -> str:
    """
    Process and respond all INVENTORY queries using a specialized INVENTORY agent.
    
    Args:
        query: given product, create a product, create a inventory, get all inventory informations, details, and check inventory healthy status.
        
    Returns:
        an inventory with all details.
    """

    logger.info("function => inventory_agent")

    # prepare the context with jwt and otel data    
    token = mainMemory.get_token()
    if not token:
        logger.error("Error, I couldn't process No JWT token available")
        return "Error, I couldn't process No JWT token available"

    context={
        "jwt":token,
        "_trace": {}, 
    }

    try:
        logger.info("Routed to Inventory Agent")

        agent_hook = AgentHook()
        all_tools = []
        
        with streamable_http_mcp_server:
            all_tools.extend(streamable_http_mcp_server.list_tools_sync())

            selected_tools = [
                t for t in all_tools 
                if t.tool_name in ["inventory_healthy", 
                                   "get_inventory",
                                   "create_inventory", 
                                   "get_product",
                                   "update_inventory"]
            ]

            logger.info(f"Available MCP tools: {[tool.tool_name for tool in selected_tools]}")

            # Create the inventory agent
            agent = Agent(name="main",
                          system_prompt=INVENTORY_SYSTEM_PROMPT,
                          model=bedrock_model, 
                          tools=selected_tools,
                          hooks=[agent_hook],
                          callback_handler=None
            )
            
            try:
                # set the traceparent fot otel link traces
                context["_trace"] = headers
                
                # Format the query for the agent and send all context data
                formatted_query = f"Please process the following query: {query} with context: {context} and extract structured information"
                
                agent_response = agent(formatted_query)
                text_response = str(agent_response)

                # Clean the message
                if len(text_response) > 0:
                    return json.dumps({
                                "status": "success",
                                "response": text_response
                })
                
                return json.dumps({
                    "status": "error",
                    "reason": "Error but I couldn't process this request due a problem. Please check if your query is clearly stated or try rephrasing it."
                })  
                
            except ToolValidationError as e:
                logger.error(f"Transaction aborted: {e}")
                return json.dumps({
                    "status": "error",
                    "reason": f"Transaction aborted: {str(e)}"
                })
        
    except Exception as e:
        logger.error(f"Error processing your query: {str(e)}")
        return json.dumps({
            "status": "error",
            "reason": f"Error processing your query: {str(e)}"
        })