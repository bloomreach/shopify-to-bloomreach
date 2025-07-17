package com.bloomreach.discovery.dish.service;

import com.bloomreach.discovery.dish.config.DockerProperties;
import com.bloomreach.discovery.dish.dto.DishConfigDTO;
import com.bloomreach.discovery.dish.dto.JobDTO;
import com.bloomreach.discovery.dish.dto.JobStatus;
import com.bloomreach.discovery.dish.exception.DockerServiceException;
import com.bloomreach.discovery.dish.util.LogContainerCallback;
import com.github.dockerjava.api.DockerClient;
import com.github.dockerjava.api.command.CreateContainerResponse;
import com.github.dockerjava.api.exception.NotFoundException;
import com.github.dockerjava.api.model.Bind;
import com.github.dockerjava.api.model.Container;
import com.github.dockerjava.api.model.HostConfig;
import com.github.dockerjava.api.model.Volume;
import jakarta.validation.Valid;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.retry.annotation.Backoff;
import org.springframework.retry.annotation.Retryable;


import java.text.MessageFormat;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Service
public class DockerService {

    private static final Logger log = LoggerFactory.getLogger(DockerService.class);

    private final DockerClient dockerClient;
    private final DockerProperties properties;

    public DockerService(DockerClient dockerClient, DockerProperties properties) {
        this.dockerClient = dockerClient;
        this.properties = properties;
    }

    @Retryable(
            retryFor = {DockerServiceException.class},
            backoff = @Backoff(delay = 2000)
    )
    public String createContainer(@Valid DishConfigDTO config) {
        try {
            List<String> environmentVariables = createEnvironmentVariables(config);
            String name = generateContainerName(config);

            boolean jobRunning = isJobRunning(generateContainerPartialName(config));

            if (!jobRunning) {
                log.info("Creating container with name: {}", name);

                CreateContainerResponse container = dockerClient.createContainerCmd(properties.getImageTag())
                        .withEnv(environmentVariables)
                        .withHostConfig(HostConfig.newHostConfig()
                                .withMemory(convertMemorySizeToBytes("4GB"))
                                .withMemorySwap(convertMemorySizeToBytes("4GB"))
                                .withMemorySwappiness(10L)
                                .withOomScoreAdj(-500)
                                .withKernelMemory(convertMemorySizeToBytes("2GB"))
                                .withBinds(new Bind(properties.getHostPath(), new Volume(properties.getExportPath())))
                        )
                        .withName(name)
                        .exec();

                log.debug("Container created with ID, using binds: {}", container.getId());

                dockerClient.startContainerCmd(container.getId()).exec();
                log.info("Container started successfully: {}", name);

                return name;
            }
            throw new IllegalStateException("Job is already RUNNING, not allowed to have multiple jobs on the same catalog");

        } catch (Exception e) {
            log.error("Failed to create Docker container", e);
            throw new DockerServiceException("Failed to create Docker container", e);
        }
    }

    private List<String> createEnvironmentVariables(DishConfigDTO config) {
        List<String> env = new ArrayList<>(Arrays.asList(
                "SHOPIFY_URL=" + config.shopifyUrl(),
                "SHOPIFY_PAT=" + config.shopifyPat(),
                "BR_ENVIRONMENT_NAME=" + config.brEnvironmentName(),
                "BR_ACCOUNT_ID=" + config.brAccountId(),
                "BR_CATALOG_NAME=" + config.brCatalogName(),
                "BR_API_TOKEN=" + config.brApiToken(),
                "BR_MULTI_MARKET=" + config.brMultiMarket(),
                "AUTO_INDEX=" + config.autoIndex()  // Add this line
        ));

        // Add market and language variables only when multi-market is enabled
        if (config.brMultiMarket()) {
            env.addAll(Arrays.asList(
                    "SHOPIFY_MARKET=" + config.shopifyMarket(),
                    "SHOPIFY_LANGUAGE=" + config.shopifyLanguage()
            ));
        }

        return env;
    }

    public String createDeltaContainer(DishConfigDTO config, Instant startDate) {
        try {
            List<String> environmentVariables = createDeltaEnvironmentVariables(config, startDate);
            String name = generateContainerName(config);

            boolean jobRunning = isJobRunning(generateContainerPartialName(config));

            if (!jobRunning) {
                log.info("Creating delta container with name: {} and start date: {}", name, startDate);

                CreateContainerResponse container = dockerClient.createContainerCmd(properties.getImageTag())
                        .withEnv(environmentVariables)
                        .withHostConfig(HostConfig.newHostConfig()
                                .withMemory(convertMemorySizeToBytes("4GB"))
                                .withMemorySwap(convertMemorySizeToBytes("4GB"))
                                .withMemorySwappiness(10L)
                                .withOomScoreAdj(-500)
                                .withKernelMemory(convertMemorySizeToBytes("2GB"))
                                .withBinds(new Bind(properties.getHostPath(), new Volume(properties.getExportPath())))
                        )
                        .withName(name)
                        .exec();

                log.debug("Delta container created with ID: {}", container.getId());

                dockerClient.startContainerCmd(container.getId()).exec();
                log.info("Delta container started successfully: {}", name);

                return name;
            }
            throw new IllegalStateException("Job is already RUNNING, not allowed to have multiple jobs on the same catalog");

        } catch (Exception e) {
            log.error("Failed to create Docker delta container", e);
            throw new DockerServiceException("Failed to create Docker delta container", e);
        }
    }

    private List<String> createDeltaEnvironmentVariables(DishConfigDTO config, Instant startDate) {
        List<String> env = new ArrayList<>(createEnvironmentVariables(config));

        String formattedStartDate = DateTimeFormatter.ISO_INSTANT.format(startDate.truncatedTo(java.time.temporal.ChronoUnit.SECONDS));
        env.add("DELTA_MODE=true");
        env.add("START_DATE=" + formattedStartDate);
        env.add("MARKET_CACHE_ENABLED=" + properties.isMarketCacheEnabled());
        env.add("MARKET_CACHE_MAX_AGE_HOURS=" + properties.getMarketCacheMaxAgeHours());

        return env;
    }

    private String generateContainerName(DishConfigDTO config) {
        return MessageFormat.format("dish-{0}-{1}-{2}-{3}", config.shopifyUrl(), config.brCatalogName(), config.brAccountId(), config.brEnvironmentName()) + "-" + System.currentTimeMillis();
    }

    private String generateContainerPartialName(DishConfigDTO config) {
        return MessageFormat.format("dish-{0}-{1}-{2}", config.shopifyUrl(), config.brCatalogName(), config.brAccountId());
    }

    @Retryable(
            retryFor = {DockerServiceException.class},
            backoff = @Backoff(delay = 2000)
    )
    public JobDTO getJobStatus(String jobName, boolean deleteOnSuccess, boolean verbose) {
        log.debug("Getting status for job: {}", jobName);

        Container container = findContainerByName(jobName);
        if (container == null) {
            throw new NotFoundException("Container not found: " + jobName);
        }

        try {
            JobDTO job = createJobWithContainer(jobName, verbose, container);

            if (deleteOnSuccess && JobStatus.SUCCESS.equals(job.jobStatus())) {
                handleSuccessfulJobDeletion(container.getId(), jobName);
            }

            return job;
        } catch (Exception e) {
            log.error("Error getting status for job: {}", jobName, e);
            throw new DockerServiceException("Failed to get job status", e);
        }
    }

    private void handleSuccessfulJobDeletion(String containerId, String jobName) {
        try {
            log.debug("Attempting to delete successful job: {}", jobName);
            dockerClient.removeContainerCmd(containerId).exec();
            log.info("Successfully deleted container for job: {}", jobName);
        } catch (Exception e) {
            log.warn("Failed to delete successful job: {}. Error: {}", jobName, e.getMessage());
            // Don't throw - this is a non-critical error
        }
    }

    private Container findContainerByName(String name) {
        log.debug("Finding container by name: {}", name);
        return dockerClient.listContainersCmd()
                .withShowAll(true)
                .exec()
                .stream()
                .filter(c -> String.format("/%s", name).equals(c.getNames()[0]))
                .findFirst()
                .orElse(null);
    }

    private boolean isJobRunning(String partialName) {
        log.debug("Finding container by partial name: {}", partialName);
        return dockerClient.listContainersCmd()
                .withShowAll(false)
                .exec()
                .stream()
                .filter(c -> c.getNames()[0].startsWith(String.format("/%s", partialName)))
                .map(obj -> true)
                .findFirst()
                .orElse(false);
    }

    private JobDTO createJobWithContainer(String jobName, boolean verbose, Container container) {
        String status = container.getStatus();
        JobStatus jobStatus = mapContainerStatusToJobStatus(status);

        String jobLog = null;
        if (verbose) {
            jobLog = getContainerLogs(container.getId());
        }

        return new JobDTO(jobName, jobStatus, jobLog);
    }

    private String getContainerLogs(String containerId) {
        try (LogContainerCallback callback = new LogContainerCallback()) {
            dockerClient.logContainerCmd(containerId)
                    .withStdErr(true)
                    .withStdOut(true)
                    .withTailAll()
                    .exec(callback);

            callback.awaitCompletion(properties.getLogTimeout(), TimeUnit.SECONDS);
            return callback.toString();
        } catch (Exception e) {
            log.warn("Failed to retrieve container logs", e);
            return "Failed to retrieve logs: " + e.getMessage();
        }
    }

    private JobStatus mapContainerStatusToJobStatus(String containerStatus) {
        if (containerStatus == null || containerStatus.trim().isEmpty()) {
            throw new IllegalArgumentException("Container status cannot be null or empty");
        }

        if (containerStatus.startsWith("Exited (")) {
            int exitCode = extractExitCode(containerStatus);
            return switch (exitCode) {
                case 0 -> JobStatus.SUCCESS;
                case 1, 137 -> JobStatus.FAILED;
                default -> throw new IllegalStateException("Unexpected exit code: " + exitCode);
            };
        }

        return JobStatus.RUNNING;
    }

    private int extractExitCode(String containerStatus) {
        try {
            int startIndex = containerStatus.indexOf("(") + 1;
            int endIndex = containerStatus.indexOf(")");
            String exitCodeStr = containerStatus.substring(startIndex, endIndex);
            return Integer.parseInt(exitCodeStr);
        } catch (Exception e) {
            throw new IllegalArgumentException("Invalid container status format: " + containerStatus);
        }
    }

    /**
     * Get status for multiple jobs by their names
     * This method only returns jobName and jobStatus (no logs)
     *
     * @param jobNames List of job names to check status for
     * @return List of JobDTO objects containing job names and statuses
     */
    @Retryable(
            retryFor = {DockerServiceException.class},
            backoff = @Backoff(delay = 2000)
    )
    public List<JobDTO> getJobStatuses(List<String> jobNames, boolean verboseOnFailure) {
        log.debug("Getting status for multiple jobs: {}", jobNames);

        try {
            List<Container> allContainers = dockerClient.listContainersCmd()
                    .withShowAll(true)
                    .exec();

            return jobNames.stream()
                    .map(jobName -> {
                        // Find the container for this job
                        Container container = allContainers.stream()
                                .filter(c -> c.getNames()[0].startsWith(String.format("/%s", jobName))) //get latest job
                                .findFirst()
                                .orElse(null);
                        if (container != null) {
                            String status = container.getStatus();
                            JobStatus jobStatus = mapContainerStatusToJobStatus(status);
                            String jobLog = null;
                            if (verboseOnFailure && JobStatus.FAILED.equals(jobStatus)) {
                                jobLog = getContainerLogs(container.getId());
                            }
                            return new JobDTO(container.getNames()[0].substring(1), jobStatus, jobLog);
                        }
                        return null;
                    })
                    .filter(Objects::nonNull)
                    .collect(Collectors.toList());
        } catch (Exception e) {
            log.error("Error getting status for multiple jobs", e);
            throw new DockerServiceException("Failed to get statuses for jobs", e);
        }
    }

    /**
     * Converts a human-readable memory size (only "MB" and "GB" units) to bytes (as a Long).
     *
     * @param memorySizeStr The memory size string (e.g. "4GB", "500MB", "4G", "500M")
     * @return The memory size in bytes as a Long
     * @throws IllegalArgumentException if the format is invalid
     */
    public static Long convertMemorySizeToBytes(String memorySizeStr) {
        if (memorySizeStr == null || memorySizeStr.trim().isEmpty()) {
            throw new IllegalArgumentException("Memory size string cannot be null or empty");
        }

        String normalizedStr = memorySizeStr.trim().toUpperCase();

        // Regex that handles both forms: GB/MB and G/M
        if (!normalizedStr.matches("^(\\d+(\\.\\d+)?)(MB?|GB?)$")) {
            throw new IllegalArgumentException("Invalid memory size format. Expected formats: 500MB/500M or 4GB/4G");
        }

        // Extract numeric part and unit with regex
        java.util.regex.Pattern pattern = java.util.regex.Pattern.compile("^(\\d+(\\.\\d+)?)(MB?|GB?)$");
        java.util.regex.Matcher matcher = pattern.matcher(normalizedStr);

        if (!matcher.find()) {
            throw new IllegalArgumentException("Failed to parse memory size: " + memorySizeStr);
        }

        double value = Double.parseDouble(matcher.group(1));
        String unit = matcher.group(3);

        // Normalize unit to include B if it's just a letter
        if (unit.length() == 1) {
            unit = unit + "B";
        }

        // Convert to bytes based on unit
        return switch (unit) {
            case "MB" -> (long) (value * 1024 * 1024);
            case "GB" -> (long) (value * 1024 * 1024 * 1024);
            default ->
                    throw new IllegalArgumentException("Unsupported memory unit: " + unit + ". Only MB and GB are supported.");
        };
    }


}

