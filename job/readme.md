# Shopify to Bloomreach Integration

This Docker container automates the extraction of product data from a Shopify store and imports it into a Bloomreach Discovery catalog using Bloomreach's Feed API.

---

## Overview

This integration performs the following operations:

1. Extracts product data from Shopify using the GraphQL Bulk Operations API
2. Transforms the data through multiple stages to match Bloomreach's requirements
3. Uploads the transformed data to your Bloomreach Discovery catalog

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

To obtain a Personal Access Token (PAT), you’ll need to create and install a custom app in your Shopify store:

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

| Variable              | Description                                                | Required    |
| --------------------- | ---------------------------------------------------------- | ----------- |
| `SHOPIFY_URL`         | Your Shopify store URL (e.g., `your-store.myshopify.com`)  | Yes         |
| `SHOPIFY_PAT`         | Your Shopify Personal Access Token                         | Yes         |
| `BR_ENVIRONMENT_NAME` | Bloomreach environment (`staging` or `production`)         | Yes         |
| `BR_ACCOUNT_ID`       | Your 4-digit Bloomreach account ID                         | Yes         |
| `BR_CATALOG_NAME`     | Your Bloomreach catalog name                               | Yes         |
| `BR_API_TOKEN`        | Your Bloomreach API token                                  | Yes         |
| `BR_OUTPUT_DIR`       | Directory for output files (default: `/export`)            | Yes         |
| `LOGLEVEL`            | Log level (default: `INFO`)                                | No          |
| `BR_MULTI_MARKET`     | Enable multi-market support (`true` or `false`)            | No          |
| `SHOPIFY_MARKET`      | Shopify market code (required if `BR_MULTI_MARKET=true`)   | Conditional |
| `SHOPIFY_LANGUAGE`    | Shopify language code (required if `BR_MULTI_MARKET=true`) | Conditional |

---

## Running the Container

### Docker Run

```bash
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

### Docker Compose

Create a `docker-compose.yml` file:

```yaml
version: '3'
services:
  dish-job:
    image: shopify-bloomreach-integration
    environment:
      - SHOPIFY_URL=your-store.myshopify.com
      - SHOPIFY_PAT=your_pat_token
      - BR_ENVIRONMENT_NAME=production
      - BR_ACCOUNT_ID=1234
      - BR_CATALOG_NAME=your-catalog
      - BR_API_TOKEN=your_bloomreach_token
      - BR_OUTPUT_DIR=/export
      - LOGLEVEL=INFO
    volumes:
      - ./export:/export
```

Then run:

```bash
docker-compose up
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

---

## Output Files

During execution, the integration generates several intermediate files in the specified output directory:

* `{timestamp}_{job_id}_shopify_bulk_op.jsonl.gz` – Raw Shopify GraphQL response
* `{timestamp}_{job_id}_1_shopify_products.jsonl.gz` – Aggregated Shopify products
* `{timestamp}_{job_id}_2_generic_products.jsonl.gz` – Generic product format
* `{timestamp}_{job_id}_3_br_products.jsonl.gz` – Bloomreach-specific product format
* `{timestamp}_{job_id}_4_br_patch.jsonl.gz` – Final Bloomreach patch operations

---

## Data Transformation Process

1. **GraphQL Extraction**: Fetches product data including variants, collections, and metafields from Shopify
2. **Shopify Products**: Aggregates related objects into complete product records
3. **Generic Products**: Transforms to intermediary format with namespace prefixes
4. **Bloomreach Products**: Maps fields to Bloomreach's expected structure
5. **Patch Creation**: Formats for Bloomreach's Feed API

---

## Troubleshooting

* **Authentication Errors**: Verify your Shopify PAT and Bloomreach API token are correct and have the required scopes
* **Processing Failures**: Check container logs for detailed error messages
* **Feed API Errors**: Ensure your Bloomreach account ID and catalog name are accurate

---

## Limitations

* All products are processed in a single batch, which may cause timeouts for large catalogs
* Product variants must have unique SKUs or IDs for correct mapping
* Custom fields are prefixed to avoid collisions with Bloomreach reserved attributes

---

## Build Custom Image

To build a custom version of the container:

```bash
docker build -t dish-job .
```

---

## License

This integration is intended for use with your Bloomreach Discovery service agreement.