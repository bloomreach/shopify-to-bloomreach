# Shopify to Bloomreach Discovery Integration

This project enables automated synchronization of Shopify product data into a Bloomreach Discovery catalog using a Dockerized workflow. It supports both **manual API triggers** and **Docker job execution**, with separation of concerns for maintainability and deployment flexibility. The system now includes **delta sync capabilities** for efficient incremental updates.

---

## 🚀 Project Structure

* **`job/`** – Contains the Docker-based ingestion logic (Python-based). This folder is responsible for:

    * Extracting product data from Shopify via GraphQL bulk operations.
    * Supporting both full feeds and delta feeds (incremental updates).
    * Transforming data into Bloomreach-compatible format.
    * Uploading the final dataset via Bloomreach's Feed API.
    * Multi-market support with translations and market-specific URLs.

* **`api-server/`** – Contains a Spring Boot REST API (Java-based) that:

    * Triggers Docker jobs on demand (full feeds).
    * Schedules and manages recurring delta feed jobs.
    * Monitors job execution status.
    * Manages security and cleanup via configurable cron jobs.
    * Provides automatic indexing capabilities.

These components are **loosely coupled** and can be run independently.

---

## 🧱 Tech Stack

* **Languages:** Python (ETL job), Java (Spring Boot API server)
* **Containerization:** Docker
* **APIs:** Shopify GraphQL, Bloomreach Feed API, Bloomreach Index API
* **Job Triggering:** REST API with token-based security
* **Scheduling:** Spring Boot dynamic scheduling with cron expressions
* **Logging:** Configurable with environment variables

---

## 📦 Docker Job (Python) – `job/`

This container automates:

1. Extraction of product and market data from Shopify (full or delta).
2. Transformation into a format compliant with Bloomreach Discovery.
3. Uploading to Bloomreach via the Feed API (PUT for full feeds, PATCH for delta feeds).
4. Optional automatic indexing after successful data upload.

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
| `BR_MULTI_MARKET`     | `true` to enable multi-market support              | No          |
| `SHOPIFY_MARKET`      | Market code (required if `BR_MULTI_MARKET=true`)   | Conditional |
| `SHOPIFY_LANGUAGE`    | Language code (required if `BR_MULTI_MARKET=true`) | Conditional |
| `AUTO_INDEX`          | `true` to auto-trigger indexing after feed         | No          |
| `DELTA_MODE`          | `true` for incremental updates                     | No          |
| `START_DATE`          | Start date for delta feeds (ISO format)            | No          |

### Feed Types

#### Full Feed (Default)
- Replaces entire product catalog
- Uses HTTP PUT to Bloomreach
- Processes all products in the store

#### Delta Feed
- Only processes products updated since last run
- Uses HTTP PATCH to Bloomreach
- Much faster for frequent updates
- Automatically calculates date ranges with 30-second overlap

### Multi-Market Support

For stores with multiple markets and translations:
- Fetches market-specific product URLs
- Includes translated product titles and descriptions
- Supports market data caching for efficient delta feeds

---

### Example Run

```bash
# Full feed
docker build -t dish-job ./job
docker run --rm -v $(pwd)/export:/export \
  -e SHOPIFY_URL=shop.myshopify.com \
  -e SHOPIFY_PAT=your_token \
  -e BR_ENVIRONMENT_NAME=production \
  -e BR_ACCOUNT_ID=1234 \
  -e BR_CATALOG_NAME=my-catalog \
  -e BR_API_TOKEN=br_token \
  -e BR_OUTPUT_DIR=/export \
  -e AUTO_INDEX=true \
  dish-job

# Delta feed
docker run --rm -v $(pwd)/export:/export \
  -e SHOPIFY_URL=shop.myshopify.com \
  -e SHOPIFY_PAT=your_token \
  -e BR_ENVIRONMENT_NAME=production \
  -e BR_ACCOUNT_ID=1234 \
  -e BR_CATALOG_NAME=my-catalog \
  -e BR_API_TOKEN=br_token \
  -e BR_OUTPUT_DIR=/export \
  -e DELTA_MODE=true \
  -e START_DATE=2025-07-16T12:00:00+00:00 \
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

---

## 🧠 API Server (Java) – `api-server/`

The API server provides an interface for programmatically managing ingestion jobs and scheduling delta feeds.

### Features

* **One-time Jobs**: Create full feed jobs via `/dish/createJob`
* **Delta Scheduling**: Schedule recurring delta feeds via `/dish/scheduleDeltaJob`
* **Job Monitoring**: Check job status via `/dish/statusJob` and `/dish/statusJobs`
* **Task Management**: List and cancel scheduled delta tasks
* **Auto-indexing**: Optional automatic index triggering after successful feeds
* **Automatic cleanup**: Scheduled removal of old containers

### Security

Enable token-based access with this config:

```yaml
dish:
  security:
    enabled: true
    access:
      token: your-secret-token
```

### API Endpoints

#### Job Management
- `POST /dish/createJob` - Create a one-time full feed job
- `GET /dish/statusJob?jobName={name}` - Check individual job status
- `GET /dish/statusJobs?jobNames={name1,name2}` - Check multiple job statuses

#### Delta Feed Scheduling
- `POST /dish/scheduleDeltaJob` - Schedule recurring delta feeds
- `GET /dish/deltaTasks` - List active scheduled tasks
- `DELETE /dish/deltaTasks/{taskId}` - Cancel a scheduled task

#### Delta Feed Intervals
- `EVERY_5_MINUTES` - Every 5 minutes
- `EVERY_15_MINUTES` - Every 15 minutes
- `EVERY_30_MINUTES` - Every 30 minutes
- `EVERY_HOUR` - Every hour
- `EVERY_2_HOURS` - Every 2 hours
- `EVERY_6_HOURS` - Every 6 hours
- `EVERY_12_HOURS` - Every 12 hours

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

### Configuration

```yaml
# application.yml
docker:
  imageTag: dish-job:latest
  exportPath: /export
  hostPath: /path/to/host/directory
  containerRetentionDays: 7

dish:
  security:
    enabled: true
    access:
      token: your-secret-token
  container:
    cleanup:
      cron: "0 0 2 * * ?"  # Daily at 2 AM
  delta:
    tracker:
      file: ./delta-job-tracker.json
```

---

## 🗂 Output Artifacts

All intermediate and final files are stored in `/export`:

* `*_shopify_bulk_op.jsonl.gz` – Raw Shopify GraphQL export
* `*_shopify_market_bulk_op.jsonl.gz` – Market data (if multi-market enabled)
* `*_1_shopify_products.jsonl` – Aggregated product objects
* `*_2_generic_products.jsonl` – Normalized format
* `*_3_br_products.jsonl` – Bloomreach-ready data
* `*_4_br_patch.jsonl` – Final patch operations for Feed API

---

## 🔄 Delta Feed Architecture

### How Delta Feeds Work

1. **Scheduling**: API server schedules recurring jobs using Spring's `@Scheduled` with cron expressions
2. **State Tracking**: File-based tracking of last successful run timestamps per catalog
3. **Date Calculation**: Automatic calculation of start dates with 30-second overlap for safety
4. **GraphQL Filtering**: Uses Shopify's `updated_at:>` query parameter to fetch only changed products
5. **API Method**: Uses HTTP PATCH instead of PUT for incremental updates
6. **Conflict Handling**: Skips execution if previous delta job is still running

### Delta Feed Benefits

- **Faster Processing**: Only processes changed products
- **Reduced Load**: Less impact on Shopify and Bloomreach APIs
- **Frequent Updates**: Enables near real-time catalog synchronization
- **Bandwidth Efficient**: Smaller data transfers

### Market Data Caching

For multi-market delta feeds, market data is cached to improve efficiency:
- Market data is cached for 24 hours by default
- Delta feeds reuse cached market data if still fresh
- Full feeds always refresh market data cache

---

## 🛠 GraphQL Query Types

The system automatically selects the appropriate GraphQL query based on configuration:

1. **Standard**: `export_data_job.graphql` - Full feed, no translations
2. **Translations**: `export_data_job_translations.graphql` - Full feed with translations
3. **Delta**: `export_data_job_delta.graphql` - Delta feed, no translations  
4. **Delta + Translations**: `export_data_job_delta_translations.graphql` - Delta feed with translations

---

## 📝 Example API Usage

### Schedule a Delta Feed

```bash
curl -X POST http://localhost:8080/dish/scheduleDeltaJob \
  -H "Content-Type: application/json" \
  -H "x-dish-access-token: your-secret-token" \
  -d '{
    "shopifyUrl": "your-store.myshopify.com",
    "shopifyPat": "your_pat_token",
    "brEnvironmentName": "production",
    "brAccountId": "1234",
    "brCatalogName": "your-catalog",
    "brApiToken": "your_br_token",
    "brMultiMarket": false,
    "autoIndex": true,
    "deltaInterval": "EVERY_15_MINUTES"
  }'
```

### Check Delta Tasks

```bash
curl -X GET http://localhost:8080/dish/deltaTasks \
  -H "x-dish-access-token: your-secret-token"
```

### Cancel Delta Task

```bash
curl -X DELETE http://localhost:8080/dish/deltaTasks/{taskId} \
  -H "x-dish-access-token: your-secret-token"
```

---

## 🧪 Development Notes

* The `combine.py` script is provided to concatenate source files for auditing or documentation purposes.
* Use it to generate a readable `combined_output.txt` containing the full source.
* Delta feed schedules are lost on application restart (designed for simplicity).
* Container cleanup runs daily to prevent resource accumulation.

---

## 🔧 Troubleshooting

### Common Issues

* **Authentication Errors**: Verify your Shopify PAT and Bloomreach API token are correct and have the required scopes
* **Processing Failures**: Check container logs for detailed error messages
* **Feed API Errors**: Ensure your Bloomreach account ID and catalog name are accurate
* **Empty Delta Feeds**: Normal behavior when no products have been updated since last run
* **Memory Issues**: Increase Docker memory allocation for large catalogs

### Delta Feed Specific Issues

* **Duplicate Products**: Check that date formats are correct (`YYYY-MM-DDTHH:MM:SS+00:00`)
* **Missing Updates**: Verify 30-second overlap is sufficient for your update frequency
* **Scheduling Issues**: Confirm cron expressions are valid and timezone-aware

---

## 📝 License

Proprietary – Bloomreach, Inc. and Contributors