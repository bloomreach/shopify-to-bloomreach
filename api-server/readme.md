# DiSh API Server (Docker-based Shopify Ingestion)

DiSh is a Spring Boot application that manages Docker-based Shopify data ingestion jobs for Bloomreach Discovery. It provides both one-time job execution and scheduled delta feed capabilities.

## Overview

DiSh provides a REST API for starting and monitoring Shopify data ingestion jobs. Each job runs in a separate Docker container, allowing for isolated and parallel processing of data from different Shopify stores into Bloomreach catalogs.

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

Configuration properties are managed through Spring's property system. Key configurations include:

### Docker Configuration

```yaml
docker:
  imageTag: dish-job:latest
  exportPath: /export
  maxConnections: 20
  connectionTimeout: 30
  responseTimeout: 45
  logTimeout: 3000
  hostPath: /path/to/host/directory
  containerRetentionDays: 7  # Days to keep containers before automatic cleanup
```

### Security Configuration

```yaml
dish:
  security:
    enabled: true
    access:
      token: your-secret-token-here
```

### Delta Feed Configuration

```yaml
dish:
  delta:
    tracker:
      file: ./delta-job-tracker.json  # File-based state tracking
  container:
    cleanup:
      cron: "0 0 2 * * ?"  # Run cleanup at 2 AM daily
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
    "interval": "EVERY_15_MINUTES",
    "createdAt": "2025-07-16T14:27:59.516",
    "lastRun": null,
    "isRunning": false
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
4. **Conflict Resolution**: Skips execution if previous delta job for the same catalog is still running
5. **GraphQL Optimization**: Uses Shopify's `updated_at:>` query to fetch only changed products
6. **API Efficiency**: Uses HTTP PATCH instead of PUT for incremental updates

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
    "lastSuccessfulRun": "2025-07-16T12:24:00.022379Z",
    "isRunning": false
  }
}
```

**Note**: Scheduled tasks are lost on application restart (by design for simplicity).

## Security

The application uses token-based authentication. To access protected endpoints, include the header:

```
x-dish-access-token: your-token-here
```

Security can be disabled for development environments by setting `dish.security.enabled=false`.

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

### Running Locally

```bash
# With security enabled
mvn spring-boot:run -Dspring-boot.run.arguments="--dish.security.access.token=your-token"

# With security disabled
mvn spring-boot:run -Dspring-boot.run.arguments="--dish.security.enabled=false"
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
dish:
  container:
    cleanup:
      cron: "0 0 2 * * ?"  # Daily at 2 AM
docker:
  containerRetentionDays: 7  # Keep containers for 7 days
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

## Docker Deployment

### Build the image
```bash
docker build -t dish-app .
```

### Run the container with Docker socket mounted
```bash
docker run -d -p 8080:8080 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e DISH_SECURITY_ACCESS_TOKEN=your-secret-token \
  -e DOCKER_HOST_PATH=/path/to/host/export \
  dish-app
```

### Docker Compose

```yaml
version: '3.8'
services:
  dish-api:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./export:/export
    environment:
      - DISH_SECURITY_ACCESS_TOKEN=your-secret-token
      - DOCKER_HOST_PATH=/path/to/host/export
      - DOCKER_CONTAINER_RETENTION_DAYS=7
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
curl -X POST http://localhost:8080/dish/createJob \
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
curl -X POST http://localhost:8080/dish/scheduleDeltaJob \
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
curl -X POST http://localhost:8080/dish/scheduleDeltaJob \
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

## License

Proprietary - Bloomreach, Inc.