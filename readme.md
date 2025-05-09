# Shopify to Bloomreach Discovery Integration

This project enables automated synchronization of Shopify product data into a Bloomreach Discovery catalog using a Dockerized workflow. It supports both **manual API triggers** and **Docker job execution**, with separation of concerns for maintainability and deployment flexibility.

---

## 🚀 Project Structure

* **`job/`** – Contains the Docker-based ingestion logic (Python-based). This folder is responsible for:

    * Extracting product data from Shopify via GraphQL bulk operations.
    * Transforming it into Bloomreach-compatible format.
    * Uploading the final dataset via Bloomreach's Feed API.

* **`api-server/`** – Contains a Spring Boot REST API (Java-based) that:

    * Triggers Docker jobs on demand.
    * Monitors job execution status.
    * Manages security and cleanup via configurable cron jobs.

These components are **loosely coupled** and can be run independently.

---

## 🧱 Tech Stack

* **Languages:** Python (ETL job), Java (Spring Boot API server)
* **Containerization:** Docker
* **APIs:** Shopify GraphQL, Bloomreach Feed API
* **Job Triggering:** REST API with token-based security
* **Logging:** Configurable with environment variables

---

## 📦 Docker Job (Python) – `job/`

This container automates:

1. Extraction of product and market data from Shopify.
2. Transformation into a format compliant with Bloomreach Discovery.
3. Uploading to Bloomreach via the Feed API.

### Required Environment Variables

| Variable              | Description                                        |
| --------------------- | -------------------------------------------------- |
| `SHOPIFY_URL`         | Shopify store URL (e.g. `shop.myshopify.com`)      |
| `SHOPIFY_PAT`         | Shopify Personal Access Token                      |
| `BR_ENVIRONMENT_NAME` | Bloomreach environment (`staging` or `production`) |
| `BR_ACCOUNT_ID`       | Bloomreach account ID (4-digit)                    |
| `BR_CATALOG_NAME`     | Bloomreach catalog name                            |
| `BR_API_TOKEN`        | Bloomreach Feed API token                          |
| `BR_OUTPUT_DIR`       | Output directory (default: `/export`)              |
| `BR_MULTI_MARKET`     | (Optional) `true` to enable multi-market           |
| `SHOPIFY_MARKET`      | (Required if `BR_MULTI_MARKET=true`)               |
| `SHOPIFY_LANGUAGE`    | (Required if `BR_MULTI_MARKET=true`)               |

---

### Example Run

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

* Create jobs via `/dish/createJob`
* Check job status via `/dish/statusJob`
* Batch status checks via `/dish/statusJobs`
* Automatic cleanup of old containers

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

## 🗂 Output Artifacts

All intermediate and final files are stored in `/export`:

* `*_shopify_bulk_op.jsonl.gz` – Raw export
* `*_1_shopify_products.jsonl` – Aggregated product objects
* `*_2_generic_products.jsonl` – Normalized format
* `*_3_br_products.jsonl` – Bloomreach-ready data
* `*_4_br_patch.jsonl` – Final patch for Feed API

---

## 🧪 Development Notes

* The `combine.py` script is provided to concatenate source files for auditing or documentation purposes.
* Use it to generate a readable `combined_output.txt` containing the full source.

---

## 📝 License

Proprietary – Bloomreach, Inc. and Contributors

