# DiSh (Docker-based Shopify Ingestion)

DiSh is a Spring Boot application that manages Docker-based Shopify data ingestion jobs for Bloomreach Discovery.

## Overview

DiSh provides a REST API for starting and monitoring Shopify data ingestion jobs. Each job runs in a separate Docker container, allowing for isolated and parallel processing of data from different Shopify stores into Bloomreach catalogs.

## Features

- Create and monitor Docker containers for Shopify data ingestion
- RESTful API with OpenAPI documentation
- Token-based authentication
- Configurable Docker settings
- Job status monitoring with optional log retrieval
- Support for multi-market Shopify configurations
- Batch job status retrieval with fault tolerance
- Optimized container lookup for performance
- Automatic cleanup of old containers via scheduled jobs

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
  container:
    cleanup:
      cron: "0 0 2 * * ?"  # Run cleanup at 2 AM daily
```

## API Endpoints

### Create Job

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
  "brMultiMarket": false
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
  "shopifyLanguage": "en-US"
}
```

### Check Job Status

Retrieves the current status of a job.

```
GET /dish/statusJob?jobName={jobName}&deleteOnSuccess={boolean}&verbose={boolean}
```

Parameters:
- `jobName`: The name of the job to check (required)
- `deleteOnSuccess`: Whether to delete the container if the job completed successfully (default: false)
- `verbose`: Whether to include detailed logs in the response (default: false)

### Check Multiple Job Statuses

Retrieves the statuses of multiple jobs in a single request.

```
GET /dish/statusJobs?jobNames={jobName1,jobName2,...}&verboseOnFailure={boolean}
```

Parameters:
- `jobNames`: Comma-separated list of job names to check (required)
- `verboseOnFailure`: Whether to include detailed logs for failed jobs (default: false)

#### Key Features of Batch Job Status:
- Fault-tolerant: continues processing even if individual jobs fail
- Optimized container lookup for better performance
- Detailed failure reporting for troubleshooting


## Security

The application uses token-based authentication. To access protected endpoints, include the header:

```
x-dish-access-token: your-token-here
```

Security can be disabled for development environments by setting `dish.security.enabled=false`.

## Docker Container

Each job runs in a Docker container with the following environment variables:

Required for all jobs:
- `SHOPIFY_URL`
- `SHOPIFY_PAT`
- `BR_ENVIRONMENT_NAME`
- `BR_ACCOUNT_ID`
- `BR_CATALOG_NAME`
- `BR_API_TOKEN`
- `BR_MULTI_MARKET`

Required for multi-market jobs:
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

## Performance Considerations

- **Container Lookup**: The application uses an optimized approach to look up containers by job name
- **Batch Operations**: Status checks for multiple jobs are handled with fault tolerance
- **Error Handling**: The system handles individual job failures gracefully without impacting other jobs
- **Connection Pooling**: Configure the `maxConnections` property based on your environment's needs
- **Resource Management**: Scheduled cleanup of old containers prevents resource leaks and improves system stability

## API Documentation

When the application is running, API documentation is available at:
- Swagger UI: `/swagger-ui/`
- OpenAPI JSON: `/v3/api-docs`

## Docker

### Build the image
```bash
docker build -t dish-app .
```

### Run the container with Docker socket mounted
```bash
docker run -d -p 8080:8080 -v /var/run/docker.sock:/var/run/docker.sock dish-app
```
## License

Proprietary - Bloomreach, Inc.