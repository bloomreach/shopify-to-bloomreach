# DiSh API Server (Docker-based Shopify Ingestion)

DiSh is a Spring Boot application that manages Docker-based Shopify data ingestion jobs for Bloomreach Discovery. It provides both one-time job execution and scheduled delta feed capabilities.

## Overview

DiSh provides a REST API for starting and monitoring Shopify data ingestion jobs. Each job runs in a separate Docker container, allowing for isolated and parallel processing of data from different Shopify stores into Bloomreach catalogs.

## 🐳 Docker Compose Setup (Recommended)

The easiest way to run the API server along with the job components is using Docker Compose from the project root:

```bash
# From project root directory
cd ..

# Create export directory (optional - Docker creates it automatically)
mkdir -p export

# Start everything
docker-compose up --build
```

This automatically:
- Builds both the job container and API server
- Configures networking and shared storage
- Starts the API server on http://localhost:8081
- Sets up automatic cleanup and monitoring

**Important**: Change the security token in `docker-compose.yml`:

```yaml
environment:
  - DISH_SECURITY_ACCESS_TOKEN=your-own-secret-token-here
```

### API Access

- **API Server**: http://localhost:8081
- **Swagger UI**: http://localhost:8081/swagger-ui/
- **Health Check**: http://localhost:8081/actuator/health

### Common Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f dish-api

# Stop services
docker-compose down

# Check status
docker-compose ps
```

## Features

- **One-time Jobs**: Create and monitor Docker containers for Shopify data ingestion
- **Delta Feed Scheduling**: Schedule recurring delta feeds with configurable intervals
- **Job Monitoring**: RESTful API with comprehensive job status tracking
- **Security**: Token-based authentication with configurable access control
- **Auto-indexing**: Optional automatic Bloomreach index triggering after successful feeds
- **Multi-market Support**: Handle Shopify stores with multiple markets and translations
- **Batch Operations**: Bulk job status retrieval with fault tolerance
- **Resource Management**: Automatic cleanup of old containers via scheduled jobs
- **Performance Optimization**: Optimized container lookup and caching strategies

## Requirements

- Java 17+
- Docker
- Spring Boot 3.x
- Maven

## Configuration

When using Docker Compose, configuration is managed through environment variables in the `docker-compose.yml` file:

### Docker Configuration

```yaml
environment:
  - DOCKER_IMAGE_TAG=dish-job:latest
  - DOCKER_EXPORT_PATH=/export
  - DOCKER_HOST_PATH=${PWD}/export
  - DOCKER_MAX_CONNECTIONS=20
  - DOCKER_CONNECTION_TIMEOUT=30
  - DOCKER_RESPONSE_TIMEOUT=45
  - DOCKER_LOG_TIMEOUT=3000
  - DOCKER_CONTAINER_RETENTION_DAYS=7
```

### Security Configuration

```yaml
environment:
  - DISH_SECURITY_ENABLED=true
  - DISH_SECURITY_ACCESS_TOKEN=your-secret-token-here
```

### Delta Feed Configuration

```yaml
environment:
  - DISH_DELTA_TRACKER_FILE=./delta-job-tracker.json
  - DISH_CONTAINER_CLEANUP_CRON=0 0 2 * * ?
```

## API Endpoints

### One-Time Job Management

#### Create Job

Creates a new Docker container to ingest Shopify data.

```
POST /dish/createJob
```

Request body:
```json
{
  "shopifyUrl": "your-store.myshopify.com",
  "shopifyPat": "your-shopify-personal-access-token",
  "brEnvironmentName": "production",
  "brAccountId": "your-br-account-id",
  "brCatalogName": "your-br-catalog-name",
  "brApiToken": "your-br-api-token",
  "brMultiMarket": false,
  "autoIndex": false
}
```

For multi-market configurations:
```json
{
  "shopifyUrl": "your-store.myshopify.com",
  "shopifyPat": "your-shopify-personal-access-token",
  "brEnvironmentName": "production",
  "brAccountId": "your-br-account-id",
  "brCatalogName": "your-br-catalog-name",
  "brApiToken": "your-br-api-token",
  "brMultiMarket": true,
  "shopifyMarket": "US",
  "shopifyLanguage": "en-US",
  "autoIndex": true
}
```

#### Check Job Status

Retrieves the current status of a job.

```
GET /dish/statusJob?jobName={jobName}&deleteOnSuccess={boolean}&verbose={boolean}
```

Parameters:
- `jobName`: The name of the job to check (required)
- `deleteOnSuccess`: Whether to delete the container if the job completed successfully (default: false)
- `verbose`: Whether to include detailed logs in the response (default: false)

#### Check Multiple Job Statuses

Retrieves the statuses of multiple jobs in a single request.

```
GET /dish/statusJobs?jobNames={jobName1,jobName2,...}&verboseOnFailure={boolean}
```

Parameters:
- `jobNames`: Comma-separated list of job names to check (required)
- `verboseOnFailure`: Whether to include detailed logs for failed jobs (default: false)

### Delta Feed Scheduling

#### Schedule Delta Job

Creates a recurring delta feed job that runs at specified intervals.

```
POST /dish/scheduleDeltaJob
```

Request body:
```json
{
  "shopifyUrl": "your-store.myshopify.com",
  "shopifyPat": "your-shopify-personal-access-token",
  "brEnvironmentName": "production",
  "brAccountId": "your-br-account-id",
  "brCatalogName": "your-br-catalog-name",
  "brApiToken": "your-br-api-token",
  "brMultiMarket": false,
  "autoIndex": true,
  "deltaInterval": "EVERY_15_MINUTES"
}
```

**Available Delta Intervals:**
- `EVERY_5_MINUTES`
- `EVERY_15_MINUTES`
- `EVERY_30_MINUTES`
- `EVERY_HOUR`
- `EVERY_2_HOURS`
- `EVERY_6_HOURS`
- `EVERY_12_HOURS`

#### List Active Delta Tasks

Retrieves all currently scheduled delta tasks.

```
GET /dish/deltaTasks
```

Response:
```json
[
  {
    "taskId": "ec186197-e5a3-409a-80a8-4da6b342f6a9",
    "catalogKey": "store.myshopify.com-catalog-1234-production",
    "interval": "EVERY_15_MINUTES"
  }
]
```

#### Cancel Delta Task

Cancels a scheduled delta task.

```
DELETE /dish/deltaTasks/{taskId}
```

Response:
```json
{
  "cancelled": true
}
```

## Delta Feed Architecture

### How Delta Feeds Work

1. **Scheduling**: Uses Spring's `TaskScheduler` with dynamic cron expressions
2. **State Tracking**: File-based tracking (`delta-job-tracker.json`) stores last successful run timestamps
3. **Date Calculation**: Automatically calculates start dates with 30-second overlap for safety
4. **GraphQL Optimization**: Uses Shopify's `updated_at:>` query to fetch only changed products
5. **API Efficiency**: Uses HTTP PATCH instead of PUT for incremental updates

### Delta Feed Benefits

- **Performance**: 10-100x faster than full feeds for incremental updates
- **Resource Efficiency**: Significantly less memory and CPU usage
- **API Optimization**: Reduces load on both Shopify and Bloomreach APIs
- **Near Real-time**: Enables frequent catalog synchronization

### State Management

Delta feeds maintain state using a JSON file that tracks:
```json
{
  "catalog-key": {
    "lastSuccessfulRun": "2025-07-16T12:24:00.022379Z"
  }
}
```

**Note**: Scheduled tasks are lost on application restart (by design for simplicity).

## Security

The application uses token-based authentication. To access protected endpoints, include the header:

```
x-dish-access-token: your-token-here
```

When using Docker Compose, update the security token in `docker-compose.yml`:

```yaml
environment:
  - DISH_SECURITY_ACCESS_TOKEN=your-own-secret-token-here
```

Generate a strong token:
```bash
# Generate random token
openssl rand -base64 32

# Or use uuidgen  
uuidgen
```

## Docker Container Environment

Each job runs in a Docker container with the following environment variables:

### Required for all jobs:
- `SHOPIFY_URL`
- `SHOPIFY_PAT`
- `BR_ENVIRONMENT_NAME`
- `BR_ACCOUNT_ID`
- `BR_CATALOG_NAME`
- `BR_API_TOKEN`

### Optional:
- `BR_MULTI_MARKET` (true/false)
- `AUTO_INDEX` (true/false)
- `DELTA_MODE` (true/false)
- `START_DATE` (ISO format with timezone)

### Required for multi-market jobs:
- `SHOPIFY_MARKET`
- `SHOPIFY_LANGUAGE`

## Job Statuses

- `CREATED`: Job has been created but may not have started yet
- `RUNNING`: Job is currently running
- `SUCCESS`: Job completed successfully
- `FAILED`: Job failed to complete

## Error Handling

The application provides standardized error responses:

```json
{
  "message": "Error description",
  "code": "ERROR_CODE",
  "timestamp": "2023-05-15T10:30:45.123"
}
```

Common error codes:
- `VALIDATION_ERROR`: Invalid input parameters
- `DOCKER_SERVICE_ERROR`: Error related to Docker operations
- `NOT_FOUND`: Requested resource not found
- `SECURITY_ERROR`: Authentication or authorization error

## Development

### Building the Application

```bash
mvn clean package
```

### Running Tests

```bash
mvn test
```

### Running Locally (Standalone)

```bash
# With security enabled
mvn spring-boot:run -Dspring-boot.run.arguments="--dish.security.access.token=your-token"

# With security disabled
mvn spring-boot:run -Dspring-boot.run.arguments="--dish.security.enabled=false"
```

### Using Docker Compose for Development

```bash
# From project root - start everything
docker-compose up --build

# View API logs
docker-compose logs -f dish-api

# Stop everything
docker-compose down
```

## Performance Considerations

- **Container Lookup**: The application uses an optimized approach to look up containers by job name
- **Batch Operations**: Status checks for multiple jobs are handled with fault tolerance
- **Error Handling**: The system handles individual job failures gracefully without impacting other jobs
- **Connection Pooling**: Configure the `maxConnections` property based on your environment's needs
- **Resource Management**: Scheduled cleanup of old containers prevents resource leaks and improves system stability
- **Delta Feed Efficiency**: Market data caching reduces redundant API calls for multi-market delta feeds

## Container Cleanup

Automatic cleanup of old containers is performed daily:

```yaml
environment:
  - DISH_CONTAINER_CLEANUP_CRON=0 0 2 * * ?  # Daily at 2 AM
  - DOCKER_CONTAINER_RETENTION_DAYS=7        # Keep containers for 7 days
```

The cleanup process:
- Only removes containers with names starting with `dish-`
- Preserves the main application container
- Configurable retention period
- Handles cleanup failures gracefully

## API Documentation

When the application is running, API documentation is available at:
- **Swagger UI**: `/swagger-ui/`
- **OpenAPI JSON**: `/v3/api-docs`

## Standalone Docker Deployment

If you need to run the API server without Docker Compose:

### Build the image
```bash
docker build -t dish-api .
```

### Run the container with Docker socket mounted
```bash
docker run -d -p 8081:8081 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e DISH_SECURITY_ACCESS_TOKEN=your-secret-token \
  -e DOCKER_HOST_PATH=/path/to/host/export \
  dish-api
```

## Monitoring and Health Checks

The application provides health check endpoints:

```
GET /actuator/health
```

Monitor delta feed execution through:
- Application logs for detailed execution information
- Job status endpoints for real-time status
- Delta task endpoints for scheduling information

## Example Usage Scenarios

### Scenario 1: One-time Full Feed
```bash
curl -X POST http://localhost:8081/dish/createJob \
  -H "Content-Type: application/json" \
  -H "x-dish-access-token: your-token" \
  -d '{
    "shopifyUrl": "store.myshopify.com",
    "shopifyPat": "shpat_...",
    "brEnvironmentName": "production",
    "brAccountId": "1234",
    "brCatalogName": "my-catalog",
    "brApiToken": "br_token",
    "autoIndex": true
  }'
```

### Scenario 2: Schedule Frequent Delta Updates
```bash
curl -X POST http://localhost:8081/dish/scheduleDeltaJob \
  -H "Content-Type: application/json" \
  -H "x-dish-access-token: your-token" \
  -d '{
    "shopifyUrl": "store.myshopify.com",
    "shopifyPat": "shpat_...",
    "brEnvironmentName": "production",
    "brAccountId": "1234",
    "brCatalogName": "my-catalog",
    "brApiToken": "br_token",
    "autoIndex": true,
    "deltaInterval": "EVERY_5_MINUTES"
  }'
```

### Scenario 3: Multi-market with Delta Feeds
```bash
curl -X POST http://localhost:8081/dish/scheduleDeltaJob \
  -H "Content-Type: application/json" \
  -H "x-dish-access-token: your-token" \
  -d '{
    "shopifyUrl": "store.myshopify.com",
    "shopifyPat": "shpat_...",
    "brEnvironmentName": "production",
    "brAccountId": "1234",
    "brCatalogName": "my-catalog",
    "brApiToken": "br_token",
    "brMultiMarket": true,
    "shopifyMarket": "US",
    "shopifyLanguage": "en",
    "autoIndex": true,
    "deltaInterval": "EVERY_15_MINUTES"
  }'
```

## Troubleshooting

### Docker Compose Issues

```bash
# Check if services are running
docker-compose ps

# View API server logs
docker-compose logs dish-api

# Check if job image was built
docker images | grep dish-job

# Verify Docker socket access
docker-compose exec dish-api ls -la /var/run/docker.sock

# Fix permissions if needed
chmod 755 export/
```

### API Issues

```bash
# Test API health
curl http://localhost:8081/actuator/health

# Check if port is available
lsof -i :8081

# Restart services
docker-compose restart dish-api
```

## License

Proprietary - Bloomreach, Inc.