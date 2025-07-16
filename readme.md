# Shopify to Bloomreach Discovery Integration

This project enables automated synchronization of Shopify product data into a Bloomreach Discovery catalog using a Dockerized workflow. It supports both **manual API triggers** and **Docker job execution**, with separation of concerns for maintainability and deployment flexibility. The system now includes **delta sync capabilities** for efficient incremental updates.

---

## 🚀 Project Structure

* **`job/`** – Contains the Docker-based ingestion logic (Python-based). This folder is responsible for:

    * Extracting product data from Shopify via GraphQL bulk operations.
    * Transforming it into Bloomreach-compatible format.
    * Uploading the final dataset via Bloomreach's Feed API.
    * **Supporting delta sync mode** for incremental updates based on timestamps.

* **`api-server/`** – Contains a Spring Boot REST API (Java-based) that:

    * Triggers Docker jobs on demand.
    * Monitors job execution status.
    * Manages security and cleanup via configurable cron jobs.
    * **Provides delta sync job creation** with automatic timestamp handling.

These components are **loosely coupled** and can be run independently.

---

## 🧱 Tech Stack

* **Languages:** Python (ETL job), Java (Spring Boot API server)
* **Containerization:** Docker
* **APIs:** Shopify GraphQL, Bloomreach Feed API
* **Job Triggering:** REST API with token-based security
* **Logging:** Configurable with environment variables
* **Data Sync:** Full and delta (incremental) synchronization modes

---

## 📦 Docker Job (Python) – `job/`

This container automates:

1. Extraction of product and market data from Shopify.
2. Transformation into a format compliant with Bloomreach Discovery.
3. Uploading to Bloomreach via the Feed API.
4. **Delta sync support** for processing only recently updated products.

### Required Environment Variables

| Variable              | Description                                        | Required    |
| --------------------- | -------------------------------------------------- | ----------- |
| `SHOPIFY_URL`         | Shopify store URL (e.g. `shop.myshopify.com`)      | Yes         |
| `SHOPIFY_PAT`         | Shopify Personal Access Token                      | Yes         |
| `BR_ENVIRONMENT_NAME` | Bloomreach environment (`staging` or `production`) | Yes         |
| `BR_ACCOUNT_ID`       | Bloomreach account ID (4-digit)                    | Yes         |
| `BR_CATALOG_NAME`     | Bloomreach catalog name                            | Yes         |
| `BR_API_TOKEN`        | Bloomreach Feed API token                          | Yes         |
| `BR_OUTPUT_DIR`       | Output directory (default: `/export`)              | Yes         |
| `BR_MULTI_MARKET`     | (Optional) `true` to enable multi-market           | No          |
| `SHOPIFY_MARKET`      | (Required if `BR_MULTI_MARKET=true`)               | Conditional |
| `SHOPIFY_LANGUAGE`    | (Required if `BR_MULTI_MARKET=true`)               | Conditional |
| `DELTA_MODE`          | (Optional) `true` to enable delta sync             | No          |
| `START_DATE`          | (Required if `DELTA_MODE=true`) ISO 8601 timestamp | Conditional |

---

### Example Run - Full Sync

```bash
docker build -t dish-job ./job
docker run --rm -v $(pwd)/export:/export \
  -e SHOPIFY_URL=shop.myshopify.com \
  -e SHOPIFY_PAT=your_token \
  -e BR_ENVIRONMENT_NAME=production \
  -e BR_ACCOUNT_ID=1234 \
  -e BR_CATALOG_NAME=my-catalog \
  -e BR_API_TOKEN=br_token \
  -e BR_OUTPUT_DIR=/export \
  dish-job
```

### Example Run - Delta Sync

```bash
docker run --rm -v $(pwd)/export:/export \
  -e SHOPIFY_URL=shop.myshopify.com \
  -e SHOPIFY_PAT=your_token \
  -e BR_ENVIRONMENT_NAME=production \
  -e BR_ACCOUNT_ID=1234 \
  -e BR_CATALOG_NAME=my-catalog \
  -e BR_API_TOKEN=br_token \
  -e BR_OUTPUT_DIR=/export \
  -e DELTA_MODE=true \
  -e START_DATE=2025-07-16T09:50:00Z \
  dish-job
```

### ⚠️ Resource Considerations

When running the `job/` component standalone (especially with large Shopify catalogs), **you may need to increase Docker's allocated memory**.

The container performs in-memory transformations and multi-step processing. To avoid `MemoryError`, it's recommended to:

* Allocate **at least 4GB of RAM** to Docker Desktop
* Use the `--memory` and `--memory-swap` flags if running via `docker run`:

```bash
docker run --rm \
  --memory=4g \
  --memory-swap=4g \
  -v $(pwd)/export:/export \
  ... # (other flags)
  dish-job
```

If using Docker Compose, add the following:

```yaml
deploy:
  resources:
    limits:
      memory: 4g
```

---

## 🧠 API Server (Java) – `api-server/`

The API server provides an interface for programmatically managing ingestion jobs.

### Features

* Create full sync jobs via `/dish/createJob`
* **Create delta sync jobs via `/dish/createDeltaJob`**
* Check job status via `/dish/statusJob`
* Batch status checks via `/dish/statusJobs`
* Automatic cleanup of old containers
* **Automatic ISO 8601 timestamp formatting for delta jobs**

### Delta Sync API

The new delta sync endpoint allows for efficient incremental updates:

```bash
POST /dish/createDeltaJob
Content-Type: application/json
x-dish-access-token: your-secret-token

{
  "shopifyUrl": "shop.myshopify.com",
  "shopifyPat": "your_token",
  "brEnvironmentName": "production",
  "brAccountId": "1234",
  "brCatalogName": "my-catalog",
  "brApiToken": "br_token",
  "brMultiMarket": false,
  "startDate": "2025-07-16T09:50:00Z"
}
```

**Key Delta Sync Features:**
- Accepts ISO 8601 timestamps with timezone support
- Automatically sets `DELTA_MODE=true` and `START_DATE` environment variables
- Truncates timestamps to seconds precision for Shopify compatibility
- Supports both UTC (`Z`) and timezone offset formats (`+02:00`)

### Security

Enable token-based access with this config:

```yaml
dish:
  security:
    enabled: true
    access:
      token: your-secret-token
```

### Build & Run

```bash
cd api-server
mvn clean package
docker build -t dish-app .
docker run -d -p 8080:8080 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e DISH_SECURITY_ACCESS_TOKEN=your-secret-token \
  dish-app
```

Swagger UI will be available at:
[http://localhost:8080/swagger-ui/](http://localhost:8080/swagger-ui/)

---

## 🔄 Delta Sync Workflow

Delta sync enables efficient incremental updates by processing only products modified since a specific timestamp.

### Recommended Delta Sync Strategy

1. **Initial Full Sync**: Start with a complete data synchronization
2. **Regular Delta Syncs**: Schedule frequent incremental updates (hourly/daily)
3. **Periodic Full Syncs**: Run complete syncs periodically to ensure data integrity
4. **Timestamp Management**: Store and track the last successful sync timestamp

### Example Workflow

```bash
# 1. Initial full sync
curl -X POST http://localhost:8080/dish/createJob \
  -H "x-dish-access-token: your-token" \
  -H "Content-Type: application/json" \
  -d '{"shopifyUrl":"shop.myshopify.com",...}'

# 2. Delta sync (1 hour later)
curl -X POST http://localhost:8080/dish/createDeltaJob \
  -H "x-dish-access-token: your-token" \
  -H "Content-Type: application/json" \
  -d '{"shopifyUrl":"shop.myshopify.com",...,"startDate":"2025-07-16T10:00:00Z"}'

# 3. Next delta sync (another hour later)
curl -X POST http://localhost:8080/dish/createDeltaJob \
  -H "x-dish-access-token: your-token" \
  -H "Content-Type: application/json" \
  -d '{"shopifyUrl":"shop.myshopify.com",...,"startDate":"2025-07-16T11:00:00Z"}'
```

### Delta Sync Benefits

- **Faster Processing**: Only processes recently updated products
- **Reduced Load**: Lower impact on both Shopify and Bloomreach APIs
- **Real-time Updates**: Enables near real-time catalog synchronization
- **Cost Efficiency**: Reduces API calls and processing time

---

## 🗂 Output Artifacts

All intermediate and final files are stored in `/export`:

* `*_shopify_bulk_op.jsonl.gz` – Raw export from Shopify
* `*_1_shopify_products.jsonl` – Aggregated product objects
* `*_2_generic_products.jsonl` – Normalized format
* `*_3_br_products.jsonl` – Bloomreach-ready data
* `*_4_br_patch.jsonl` – Final patch for Feed API

**Delta sync files** contain only the subset of products updated since the specified `START_DATE`, making them significantly smaller and faster to process than full sync outputs.

---

## 🕐 Timestamp Handling

The system handles various timestamp formats for maximum flexibility:

### Supported Formats

- **UTC**: `2025-07-16T09:50:00Z`
- **With Timezone**: `2025-07-16T09:50:00+02:00`
- **Short Timezone**: `2025-07-16T09:50:00+0200`

### Automatic Processing

The API server automatically:
1. Converts timestamps to ISO 8601 format
2. Truncates to seconds precision (removes milliseconds)
3. Formats for optimal Shopify GraphQL compatibility
4. Logs the formatted timestamp for debugging

### GraphQL Query Format

The delta sync uses properly quoted timestamps in Shopify GraphQL queries:

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

**Important**: The single quotes around the timestamp are crucial for proper parsing by Shopify's GraphQL API.

---

## 🧪 Development Notes

* The `combine.py` script is provided to concatenate source files for auditing or documentation purposes.
* Use it to generate a readable `combined_output.txt` containing the full source.
* **Delta sync development**: Test with recent timestamps to verify filtering works correctly
* **Timezone testing**: Verify your local timezone handling matches expected behavior

---

## 🚀 Production Deployment Recommendations

### For Delta Sync in Production

1. **Monitoring**: Track delta sync frequency and success rates
2. **Overlap Strategy**: Use a small time overlap (5-10 minutes) to account for timing discrepancies
3. **Fallback**: Implement automatic fallback to full sync if delta sync fails repeatedly
4. **Scheduling**: Consider these intervals:
   - **High-frequency stores**: Every 15-30 minutes
   - **Medium-frequency stores**: Every 1-2 hours  
   - **Low-frequency stores**: Every 4-6 hours
   - **Full sync backup**: Daily or weekly

### Example Production Schedule

```bash
# Hourly delta sync (cron: 0 * * * *)
curl -X POST http://api-server:8080/dish/createDeltaJob \
  -H "x-dish-access-token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{...\"startDate\":\"$(date -d '1 hour ago' -Iseconds | sed 's/+00:00/Z/')\"}"

# Daily full sync (cron: 0 2 * * *)
curl -X POST http://api-server:8080/dish/createJob \
  -H "x-dish-access-token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{...}"
```

---

## 🔧 Troubleshooting Delta Sync

### Common Issues

1. **GraphQL Parsing Errors**: 
   - Ensure timestamps are properly quoted with single quotes
   - Verify ISO 8601 format compliance
   - Check for unsupported timezone formats

2. **No Products Found**:
   - Verify the `START_DATE` is not too recent
   - Check that products have been actually updated since the timestamp
   - Ensure timezone conversion is correct

3. **Timestamp Format Issues**:
   - Use seconds precision (no milliseconds)
   - Ensure proper timezone offset format (`+02:00` not `+2`)
   - Verify UTC conversion when using local timestamps

### Debug Commands

```bash
# Check job logs for timestamp formatting
curl "http://localhost:8080/dish/statusJob?jobName=delta-job-123&verbose=true" \
  -H "x-dish-access-token: your-token"

# Test timestamp format manually
echo "2025-07-16T09:50:00Z" | date -d @$(date -d "2025-07-16T09:50:00Z" +%s) -Iseconds
```

---

## 📝 License

Proprietary – Bloomreach, Inc. and Contributors