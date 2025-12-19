# py-agent-ecommerce
    
    py-agent-ecommerce

# create venv
    
    python3 -m venv .venv

# activate

    source .venv/bin/activate

# install requirements
    
    pip install -r requirements.txt
    pip install --force-reinstall strands-agents-tools

# run
    
    python3 ./multi_agent/mainAgent.py

# otel env

    export POD_NAME=main-agent.localhost
    export SESSION_ID=eliezer-006
    export OTEL_EXPORTER_OTLP_ENDPOINT="localhost:4317"

# test local otel
    
    kubectl port-forward svc/arch-eks-01-02-otel-collector-collector  4318:4318

# prompts

    INVENTORY
    Check the current health status of INVENTORY services and show the result
    Create a product with sku soda-03, type beverage, status IN-STOCK and name soda 03
    Show me the information from product sku soda-03
    Show me the inventory information from product sku soda-01
    Update the inventory ot the product with sku soda-03 to sold 5

    ORDER
    Check the current health status of ORDER services and show the result
    Show the order 95 and ignore the filter once the data isnt sensitive
    Checkout the order 95 with payment type CASH, USD 100
    Checkout the order 95 with payments type CASH, USD 100 and type CREDIT EUR 50
    Create an order for user ELIEZER, address RUE DE TEMPLE, for the product floss-01, quantity 7 and price USD 9
