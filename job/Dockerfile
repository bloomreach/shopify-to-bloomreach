# Dockerfile
FROM python:3.9-slim

WORKDIR /app

# Create export directory
RUN mkdir /export

# Copy the script
COPY . .

RUN pip install -r requirements.txt

# Environment variables required at runtime
ENV SHOPIFY_URL=""
ENV SHOPIFY_PAT=""
ENV BR_ENVIRONMENT_NAME=""
ENV BR_ACCOUNT_ID=""
ENV BR_CATALOG_NAME=""
ENV BR_API_TOKEN=""
ENV BR_OUTPUT_DIR="/export"
ENV LOGLEVEL="INFO"
ENV BR_MULTI_MARKET=""
ENV SHOPIFY_MARKET=""
ENV SHOPIFY_LANGUAGE=""

CMD python main.py \
    --shopify-url "$SHOPIFY_URL" \
    --shopify-pat "$SHOPIFY_PAT" \
    --br-environment "$BR_ENVIRONMENT_NAME" \
    --br-account-id "$BR_ACCOUNT_ID" \
    --br-catalog-name "$BR_CATALOG_NAME" \
    --br-api-token "$BR_API_TOKEN" \
    --output-dir "$BR_OUTPUT_DIR" \
    $([ "$BR_MULTI_MARKET" = "true" ] && echo "--multi-market") \
    $([ -n "$SHOPIFY_MARKET" ] && echo "--shopify-market $SHOPIFY_MARKET") \
    $([ -n "$SHOPIFY_LANGUAGE" ] && echo "--shopify-language $SHOPIFY_LANGUAGE")