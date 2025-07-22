# Shopify to Bloomreach Integration Job

This Docker container automates the extraction of product data from a Shopify store and imports it into a Bloomreach Discovery catalog using Bloomreach's Feed API. It supports both full feeds and incremental delta feeds.

---

## Overview

This integration performs the following operations:

1. Extracts product data from Shopify using the GraphQL Bulk Operations API
2. Supports both full feeds (all products) and delta feeds (only updated products)
3. Transforms the data through multiple stages to match Bloomreach's requirements
4. Uploads the transformed data to your Bloomreach Discovery catalog
5. Optionally triggers automatic indexing after successful data upload
6. Supports multi-market stores with translations and market-specific URLs

---

## Prerequisites

* A Shopify store with Admin API access
* A Shopify Personal Access Token (PAT) with the following scopes:

    * `read_markets`
    * `read_products`
    * `read_translations`
* A Bloomreach Discovery account with Feed API access
* Bloomreach account ID, catalog name, and API token

---

## Creating the Shopify Access Token

To obtain a Personal Access Token (PAT), you'll need to create and install a custom app in your Shopify store:

1. Go to your Shopify admin interface
2. Click **Settings** at the bottom of the left navigation
3. Select **Apps and sales channels**
4. Click **Develop apps**
5. Click **Create an app**
6. Name it (e.g., "Bloomreach Integration")
7. Click **Configure Admin API scopes**
8. Select the following scopes:

    * `read_products`
    * `read_markets`
    * `read_translations`
9. Click **Save**
10. Click **Install app** and confirm
11. Click **Reveal token once** and copy the token — this will be your `SHOPIFY_PAT` environment variable

> ⚠️ **Note**: This token will only be shown once. Save it securely.

---

## Environment Variables

Set the following environment variables before running the container:

| Variable              | Description                                                | Required    | Default |
| --------------------- | ---------------------------------------------------------- | ----------- | ------- |
| `SHOPIFY_URL`         | Your Shopify store URL (e.g., `your-store.myshopify.com`)  | Yes         | -       |
| `SHOPIFY_PAT`         | Your Shopify Personal Access Token                         | Yes         | -       |
| `BR_ENVIRONMENT_NAME` | Bloomreach environment (`staging` or `production`)         | Yes         | -       |
| `BR_ACCOUNT_ID`       | Your 4-digit Bloomreach account ID                         | Yes         | -       |
| `BR_CATALOG_NAME`     | Your Bloomreach catalog name                               | Yes         | -       |
| `BR_API_TOKEN`        | Your Bloomreach API token                                  | Yes         | -       |
| `BR_OUTPUT_DIR`       | Directory for output files                                 | Yes         | `/export` |
| `LOGLEVEL`            | Log level                                                  | No          | `INFO`   |
| `BR_MULTI_MARKET`     | Enable multi-market support (`true` or `false`)            | No          | `false`  |
| `SHOPIFY_MARKET`      | Shopify market code (required if `BR_MULTI_MARKET=true`)   | Conditional | -       |
| `SHOPIFY_LANGUAGE`    | Shopify language code (required if `BR_MULTI_MARKET=true`) | Conditional | -       |
| `AUTO_INDEX`          | Automatically trigger indexing after feed upload (`true` or `false`) | No | `false` |
| `DELTA_MODE`          | Enable delta feed mode (`true` or `false`)                 | No          | `false`  |
| `START_DATE`          | Start date for delta feeds (ISO format with timezone)      | No          | -       |

---

## Feed Types

### Full Feed (Default)
Processes all products in your Shopify store and replaces the entire Bloomreach catalog.

```bash
docker build -t dish-job .
docker run -e SHOPIFY_URL=your-store.myshopify.com \
  -e SHOPIFY_PAT=your_pat_token \
  -e BR_ENVIRONMENT_NAME=production \
  -e BR_ACCOUNT_ID=1234 \
  -e BR_CATALOG_NAME=your-catalog \
  -e BR_API_TOKEN=your_bloomreach_token \
  -e BR_OUTPUT_DIR=/export \
  -v /local/path:/export \
  dish-job
```

### Delta Feed
Processes only products that have been updated since a specified date. Much faster for frequent updates.

```bash
docker run -e SHOPIFY_URL=your-store.myshopify.com \
  -e SHOPIFY_PAT=your_pat_token \
  -e BR_ENVIRONMENT_NAME=production \
  -e BR_ACCOUNT_ID=1234 \
  -e BR_CATALOG_NAME=your-catalog \
  -e BR_API_TOKEN=your_bloomreach_token \
  -e BR_OUTPUT_DIR=/export \
  -e DELTA_MODE=true \
  -e START_DATE=2025-07-16T12:00:00+00:00 \
  -v /local/path:/export \
  dish-job
```

---

## Multi-Market Support

For multi-market stores, enable the multi-market feature and specify your market and language:

```bash
docker run -e SHOPIFY_URL=your-store.myshopify.com \
  -e SHOPIFY_PAT=your_pat_token \
  -e BR_ENVIRONMENT_NAME=production \
  -e BR_ACCOUNT_ID=1234 \
  -e BR_CATALOG_NAME=your-catalog \
  -e BR_API_TOKEN=your_bloomreach_token \
  -e BR_OUTPUT_DIR=/export \
  -e BR_MULTI_MARKET=true \
  -e SHOPIFY_MARKET=us \
  -e SHOPIFY_LANGUAGE=en \
  -v /local/path:/export \
  dish-job
```

### Multi-Market Features
- Fetches translated product titles and descriptions
- Generates market-specific product URLs
- Supports market data caching for efficient delta feeds
- Compatible with both full and delta feed modes

---

## Auto-Indexing

Enable automatic indexing to make your catalog data searchable immediately after upload:

```bash
docker run -e SHOPIFY_URL=your-store.myshopify.com \
  -e SHOPIFY_PAT=your_pat_token \
  -e BR_ENVIRONMENT_NAME=production \
  -e BR_ACCOUNT_ID=1234 \
  -e BR_CATALOG_NAME=your-catalog \
  -e BR_API_TOKEN=your_bloomreach_token \
  -e BR_OUTPUT_DIR=/export \
  -e AUTO_INDEX=true \
  -v /local/path:/export \
  dish-job
```

---

## Output Files

During execution, the integration generates several intermediate files in the specified output directory:

* `{timestamp}_{job_id}_shopify_bulk_op.jsonl.gz` – Raw Shopify GraphQL response
* `{timestamp}_{job_id}_shopify_market_bulk_op.jsonl.gz` – Market data (if multi-market enabled)
* `{timestamp}_{job_id}_1_shopify_products.jsonl.gz` – Aggregated Shopify products
* `{timestamp}_{job_id}_2_generic_products.jsonl.gz` – Generic product format
* `{timestamp}_{job_id}_3_br_products.jsonl.gz` – Bloomreach-specific product format
* `{timestamp}_{job_id}_4_br_patch.jsonl.gz` – Final Bloomreach patch operations

When using Docker Compose, these files are stored in the `./export/` directory on your host machine.

---

## Data Transformation Process

1. **GraphQL Extraction**: Fetches product data including variants, collections, and metafields from Shopify
2. **Shopify Products**: Aggregates related objects into complete product records
3. **Generic Products**: Transforms to intermediary format with namespace prefixes
4. **Bloomreach Products**: Maps fields to Bloomreach's expected structure
5. **Patch Creation**: Formats for Bloomreach's Feed API
6. **Feed Upload**: Uploads to Bloomreach using PUT (full feeds) or PATCH (delta feeds)
7. **Indexing** (Optional): Triggers index update to make data searchable

---

## GraphQL Query Selection

The container automatically selects the appropriate GraphQL query based on your configuration:

| Mode | Multi-Market | Query File |
|------|--------------|------------|
| Full Feed | No | `export_data_job.graphql` |
| Full Feed | Yes | `export_data_job_translations.graphql` |
| Delta Feed | No | `export_data_job_delta.graphql` |
| Delta Feed | Yes | `export_data_job_delta_translations.graphql` |

---

## Command Line Usage

You can also run the Python script directly:

```bash
# Full feed
python main.py \
  --shopify-url your-store.myshopify.com \
  --shopify-pat your_pat_token \
  --br-environment production \
  --br-account-id 1234 \
  --br-catalog-name your-catalog \
  --br-api-token your_br_token \
  --output-dir /export \
  --auto-index

# Delta feed
python main.py \
  --shopify-url your-store.myshopify.com \
  --shopify-pat your_pat_token \
  --br-environment production \
  --br-account-id 1234 \
  --br-catalog-name your-catalog \
  --br-api-token your_br_token \
  --output-dir /export \
  --delta-mode \
  --start-date 2025-07-16T12:00:00+00:00

# Multi-market with delta
python main.py \
  --shopify-url your-store.myshopify.com \
  --shopify-pat your_pat_token \
  --br-environment production \
  --br-account-id 1234 \
  --br-catalog-name your-catalog \
  --br-api-token your_br_token \
  --output-dir /export \
  --multi-market \
  --shopify-market us \
  --shopify-language en \
  --delta-mode \
  --start-date 2025-07-16T12:00:00+00:00
```

---

## Troubleshooting

### Common Issues

* **Authentication Errors**: Verify your Shopify PAT and Bloomreach API token are correct and have the required scopes
* **Processing Failures**: Check container logs for detailed error messages
* **Feed API Errors**: Ensure your Bloomreach account ID and catalog name are accurate
* **Memory Issues**: Increase Docker memory allocation for large catalogs (recommended: 4GB+)

### Delta Feed Specific Issues

* **Empty Delta Feeds**: Normal behavior when no products have been updated since the start date
* **Date Format Errors**: Ensure `START_DATE` is in ISO format with timezone: `YYYY-MM-DDTHH:MM:SS+00:00`
* **Missing Products**: Verify the start date is not too recent; try extending the time window

### Multi-Market Issues

* **Missing Translations**: Ensure your Shopify store has translations configured for the specified language
* **Market Data Errors**: Verify your store has multiple markets configured and published

---

## Performance Optimization

### Memory Usage
For large catalogs (10,000+ products), allocate at least 4GB of memory to Docker:

```bash
docker run --memory=4g --memory-swap=4g \
  -e SHOPIFY_URL=your-store.myshopify.com \
  # ... other environment variables
  dish-job
```

### Delta Feed Benefits
- **Speed**: 10-100x faster than full feeds for incremental updates
- **Resource Usage**: Significantly less memory and CPU for small changes
- **API Limits**: Reduces load on both Shopify and Bloomreach APIs

---

## Build Custom Image

To build a custom version of the container:

```bash
docker build -t dish-job .
```

---

## License

This integration is intended for use with your Bloomreach Discovery service agreement.