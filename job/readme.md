# Shopify to Bloomreach Integration

This Docker container automates the extraction of product data from a Shopify store and imports it into a Bloomreach Discovery catalog using Bloomreach's Feed API.

---

## Overview

This integration performs the following operations:

1. Extracts product data from Shopify using the GraphQL Bulk Operations API
2. Transforms the data through multiple stages to match Bloomreach's requirements
3. Uploads the transformed data to your Bloomreach Discovery catalog
4. **Supports delta sync mode** for incremental updates based on timestamps

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
| `DELTA_MODE`          | Enable delta sync mode (`true` or `false`)                 | No          |
| `START_DATE`          | ISO 8601 timestamp for delta sync start point             | Conditional |

### Delta Sync Variables

When `DELTA_MODE=true`, the following additional behavior applies:

- `START_DATE`: Must be provided in ISO 8601 format (e.g., `2025-07-16T09:50:00Z`)
- The job will only process products updated after the `START_DATE` timestamp
- Supports timezone-aware timestamps (e.g., `2025-07-16T09:50:00+02:00`)
- Uses optimized GraphQL queries with timestamp filtering

---

## Running the Container

### Docker Run - Full Sync

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

### Docker Run - Delta Sync

```bash
docker run -e SHOPIFY_URL=your-store.myshopify.com \
  -e SHOPIFY_PAT=your_pat_token \
  -e BR_ENVIRONMENT_NAME=production \
  -e BR_ACCOUNT_ID=1234 \
  -e BR_CATALOG_NAME=your-catalog \
  -e BR_API_TOKEN=your_bloomreach_token \
  -e BR_OUTPUT_DIR=/export \
  -e DELTA_MODE=true \
  -e START_DATE=2025-07-16T09:50:00Z \
  -v /local/path:/export \
  dish-job
```

### Docker Compose

Create a `docker-compose.yml` file:

```yaml
version: '3'
services:
  # Full sync job
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

  # Delta sync job
  dish-job-delta:
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
      - DELTA_MODE=true
      - START_DATE=2025-07-16T09:50:00Z
    volumes:
      - ./export:/export
```

Then run:

```bash
# For full sync
docker-compose up dish-job

# For delta sync
docker-compose up dish-job-delta
```

---

## Delta Sync Mode

Delta sync allows for efficient incremental updates by processing only products that have been modified since a specific timestamp.

### How It Works

1. **GraphQL Query Optimization**: When `DELTA_MODE=true`, the container uses timestamp-filtered queries:
   ```graphql
   products (query: "updated_at:>'2025-07-16T09:50:00Z'") {
     edges {
       node {
         id
         handle
         title
         updatedAt
       }
     }
   }
   ```

2. **Timestamp Handling**: The `START_DATE` is formatted to ISO 8601 standard and truncated to seconds precision for optimal compatibility with Shopify's GraphQL API.

3. **Timezone Support**: Accepts various timestamp formats:
   - UTC: `2025-07-16T09:50:00Z`
   - With timezone offset: `2025-07-16T09:50:00+02:00`
   - Will be properly converted for Shopify API compatibility

### Delta Sync Best Practices

- **Store Last Sync Time**: Keep track of the last successful sync timestamp for the next delta job
- **Overlap Strategy**: Consider using a small overlap (e.g., subtract 5 minutes) to account for potential timing issues
- **Frequency**: Run delta syncs frequently (hourly/daily) for near real-time updates
- **Full Sync Backup**: Schedule periodic full syncs to ensure data integrity
- **Monitor Results**: Check that expected products are being processed in delta mode

### Example Delta Sync Workflow

```bash
# Initial full sync
docker run ... dish-job

# Later delta sync (e.g., from last successful run + 5 min buffer)
docker run -e DELTA_MODE=true -e START_DATE=2025-07-16T09:45:00Z ... dish-job

# Next delta sync
docker run -e DELTA_MODE=true -e START_DATE=2025-07-16T11:30:00Z ... dish-job
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

**Multi-market + Delta Sync:**
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
  -e DELTA_MODE=true \
  -e START_DATE=2025-07-16T09:50:00Z \
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

**Delta sync files** follow the same naming convention but will contain only the subset of products updated since the `START_DATE`.

---

## Data Transformation Process

1. **GraphQL Extraction**: Fetches product data including variants, collections, and metafields from Shopify
   - In delta mode: Applies `updated_at` timestamp filtering
2. **Shopify Products**: Aggregates related objects into complete product records
3. **Generic Products**: Transforms to intermediary format with namespace prefixes
4. **Bloomreach Products**: Maps fields to Bloomreach's expected structure
5. **Patch Creation**: Formats for Bloomreach's Feed API

---

## Troubleshooting

* **Authentication Errors**: Verify your Shopify PAT and Bloomreach API token are correct and have the required scopes
* **Processing Failures**: Check container logs for detailed error messages
* **Feed API Errors**: Ensure your Bloomreach account ID and catalog name are accurate
* **Delta Sync Issues**: 
  - Verify `START_DATE` format is correct ISO 8601
  - Check that the timestamp is not too far in the future
  - Ensure timezone offsets are properly formatted (e.g., `+02:00` not `+2`)
  - Review GraphQL query parsing in container logs

---

## Limitations

* All products are processed in a single batch, which may cause timeouts for large catalogs
* Product variants must have unique SKUs or IDs for correct mapping
* Custom fields are prefixed to avoid collisions with Bloomreach reserved attributes
* **Delta sync limitations**:
  - Only processes products based on `updated_at` timestamp
  - Does not handle deleted products (use full sync periodically)
  - Timestamp precision is limited to seconds

---

## Build Custom Image

To build a custom version of the container:

```bash
docker build -t dish-job .
```

---

## License

This integration is intended for use with your Bloomreach Discovery service agreement.