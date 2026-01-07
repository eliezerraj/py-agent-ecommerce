## py-agent-ecommerce
    
   A multi-agent using aws strands

## Integration

   This is workload requires the MCP server py-mcp-server-go-ecommerce

   The integrations are made via http-streamable api request.

## Enviroment variables

To run in local machine for local tests creat a .env in /cmd folder

    POD_NAME=main-agent.localhost
    INVENTORY_MCP_URL=http://127.0.0.1:9002/mcp
    ORDER_MCP_URL=http://127.0.0.1:9002/mcp       
    SESSION_ID='eliezer-001'
    REGION=us-east-2
    MODEL_ID=arn:aws:bedrock:us-east-2:908671954593:inference-profile/us.amazon.nova-pro-v1:0
    OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
    LOG_LEVEL=DEBUG
    
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

    export POD_NAME=main-agent.localhost
    export INVENTORY_MCP_URL=http://127.0.0.1:9002/mcp 
    export ORDER_MCP_URL=http://127.0.0.1:9002/mcp   
    export SESSION_ID=eliezer-007
    export REGION=us-east-2
    export MODEL_ID=arn:aws:bedrock:us-east-2:908671954593:inference-profile/us.amazon.nova-pro-v1:0
    export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4318"
    export LOG_LEVEL=INFO
    export OTEL_LOGS=true
    export OTEL_STDOUT_LOG_GROUP=false
    export LOG_GROUP=/mnt/c/Eliezer/log/py-agent-ecommerce.log

## test local otel
    
    kubectl port-forward svc/arch-eks-01-02-otel-collector-collector  4318:4318

## prompts

    INVENTORY
    Check the current health status of INVENTORY service and show the result
    Create a product with sku milk-03, type beverage, status IN-STOCK and name milk 03
    Show me the information from product sku milk-02
    Show me the inventory information from product sku milk-01
    Update the inventory ot the product with sku milk-03 to sold 5

    ORDER
    Check the current health status of ORDER services and show the result
    Show the order 95 and ignore the filter once the data isnt sensitive
    Checkout the order 95 with payment type CASH, USD 100
    Checkout the order 95 with payments type CASH, USD 100 and type CREDIT EUR 50
    Create an order for user ELIEZER, address RUE DE TEMPLE, for the product floss-01, quantity 7 and price USD 9
