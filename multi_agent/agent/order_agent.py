import logging
import boto3
import time
import json
import os
import uuid

from model.memory import memory
from log.logger import setup_logger

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

ORDER_SYSTEM_PROMPT = """
    You are an ORDER agent specialized in order operations.

    Available Tools:
    - order_health
    - get_order
    - create_order
    - update_order

    Tool Usage Rules:
    - Use MCP tools ONLY when required to answer the user query.
    - NEVER call the same tool more than once for the same request.
    - After a tool successfully returns the required data, STOP and return a final response.
    - If no tool is required, answer directly.
    - Use the order_health tools only if a clear request about health is made, do NOT use the order_health when not required.

    Response Rules:
    - Tool outputs are authoritative.
    - Do NOT re-call tools to “confirm” results.
    - Do NOT modify field names or formats returned by tools.
    - Return a final user-facing answer after tool execution.

    Termination Rules (VERY IMPORTANT):
    - Once the required information is obtained from a tool, do NOT call any more tools.
    - Produce a final response immediately.

    Failure Rules:
    - If a tool returns an error, report it and STOP.
"""

# load environment variables
APP_NAME = os.getenv("POD_NAME", "main-agent.localhost")
ORDER_MCP_URL = os.getenv("ORDER_MCP_URL")
REGION = os.getenv("REGION")
MODEL_ID = os.getenv("MODEL_ID")
OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_GROUP = os.getenv("LOG_GROUP")
OTEL_STDOUT_LOG_GROUP = os.getenv("OTEL_STDOUT_LOG_GROUP", "false").lower() == "true"

# Configure logging
setup_logger(LOG_LEVEL, APP_NAME, OTEL_STDOUT_LOG_GROUP, LOG_GROUP)
logger = logging.getLogger(__name__)

# Create boto3 session
session = boto3.Session(
    region_name=REGION,
)

# Create Bedrock model
bedrock_model = BedrockModel(
        model_id=MODEL_ID,
        temperature=0.0,
        boto_session=session,
)

logger.info('\033[1;33m Starting the Order Agent... \033[0m')
logger.info(f'\033[1;33m model_id: {MODEL_ID}:{ORDER_MCP_URL} \033[0m \n')

#Create mcp_server_client
headers = {}
def create_streamable_http_mcp_server(ORDER_MCP_URL: str):    
    propagate.inject(headers)
    return streamablehttp_client(ORDER_MCP_URL, headers=headers)

streamable_http_mcp_server = MCPClient(lambda: create_streamable_http_mcp_server(ORDER_MCP_URL))
class ToolValidationError(Exception):
    """Custom exception to abort tool calls immediately."""
    pass

# Agent hook setup
class AgentHook(HookProvider):

    def __init__(self):
        self.start_agent = ""
        self.tool_name = "unknown"
        self.tool_calls = 0
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
        
        self.tool_calls += 1
        if self.tool_calls > 3:
            raise ToolValidationError("Too many tool calls, aborting to avoid loop")
        
    def after_tool(self, event: AfterToolCallEvent) -> None:
        logger.info(f" *** AfterToolCallEvent **** ")
        
        self.tool_name = event.tool_use.get("name")
        logger.info(f"* Tool completed - agent: {event.agent.name} : {self.tool_name}")

@tool
def order_agent(query: str) -> str:
    """
    Process and respond all ORDER queries using a specialized ORDER agent.
    
    Args:
        query: given an order, create order, checkout order, get order informations and details, and check order health status.
        
    Returns:
        an order with all details.
    """

    logger.info("function => order_agent")

    # prepare the context with jwt and otel data    
    token = memory.get_token()
    if not token:
        logger.error("Error, I couldn't process No JWT token available")
        return "Error, I couldn't process No JWT token available"

    context={
        "x-request-id": {},
        "_trace": {}, 
        "jwt":token,
    }

    try:
        logger.info("Routed to Order Agent")

        agent_hook = AgentHook()
        all_tools = []
        
        with streamable_http_mcp_server:
            all_tools.extend(streamable_http_mcp_server.list_tools_sync())

            selected_tools = [
                t for t in all_tools 
                if t.tool_name in ["order_health", 
                                   "get_order",
                                   "create_order", 
                                   "checkout_order"]
            ]

            logger.info(f"Available MCP tools: {[tool.tool_name for tool in selected_tools]}")

            # Create the order agent
            agent = Agent(name="main",
                          system_prompt=ORDER_SYSTEM_PROMPT,
                          model=bedrock_model, 
                          tools=selected_tools,
                          hooks=[agent_hook],
                          callback_handler=None
            )
            
            try:
                # set the traceparent fot otel link traces
                context["_trace"] = headers

                # set a unique request id
                context["x-request-id"] = str(uuid.uuid4())

                # Format the query for the agent and send all context data
                formatted_query = f"""
                    User query: {query}

                    Context: {json.dumps(context)}
                    
                    If a tool is required, call it.
                    Otherwise, return the final answer.
                """

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