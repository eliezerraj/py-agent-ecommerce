## py-agent-ecommerce
    
   A multi-agent using aws strands

## Integration

   This is workload requires the MCP server py-mcp-server-go-ecommerce

   The integrations are made via http-streamable api request.

## Enviroment variables

To run in local machine for local tests creat a .env in /cmd folder

    APP_NAME=main-agent.localhost
    INVENTORY_MCP_URL=http://127.0.0.1:9002/mcp 
    ORDER_MCP_URL=http://127.0.0.1:9002/mcp   
    SESSION_ID=eliezer-007
    REGION=us-east-2
    MODEL_ID=arn:aws:bedrock:us-east-2:908671954593:inference-profile/us.amazon.nova-pro-v1:0
    OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4318"
    LOG_LEVEL=INFO
    OTEL_STDOUT_LOG_GROUP=True
    LOG_GROUP=/mnt/c/Eliezer/log/py-agent-ecommerce.log


## create venv
    
    python3 -m venv .venv

## activate

    source .venv/bin/activate

## install requirements
    
    pip install -r requirements.txt
    pip install --force-reinstall strands-agents-tools

## run
    
    python3 ./multi_agent/main.py

## enviroment variables

    export APP_NAME=main-agent.localhost
    export INVENTORY_MCP_URL=http://127.0.0.1:9002/mcp 
    export ORDER_MCP_URL=http://127.0.0.1:9002/mcp   
    export SESSION_ID=eliezer-007
    export REGION=us-east-2
    export MODEL_ID=arn:aws:bedrock:us-east-2:908671954593:inference-profile/us.amazon.nova-pro-v1:0
    export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4318"
    export LOG_LEVEL=INFO
    export OTEL_STDOUT_LOG_GROUP=True
    export LOG_GROUP=/mnt/c/Eliezer/log/py-agent-ecommerce.log

## test local otel
    
    kubectl port-forward svc/arch-eks-01-02-otel-collector-collector  4318:4318

## prompts

    INVENTORY

    Check the current health status of INVENTORY service and show the result
    Create a product with sku coffee-23, type beverage, status IN-STOCK and name coffee 23
    Show me only product information sku coffee-23  	
    Show me the inventory of the product sku coffee-23
    Update the inventory ot the product with sku coffee-23 to available 500

    ORDER
    
    Check the current health status of ORDER services and show the result
    Show me the order 121 and ignore all possibles filters, all data is not sensitive
    Checkout the order 121 with payment type CASH, USD 120
    Checkout the order 118 with payments type CASH, USD 100 and type CREDIT EUR 50
    Create an order for user ELIEZER with address RUE DE TEMPLE for the product coffee-22, quantity 5 and price USD 10