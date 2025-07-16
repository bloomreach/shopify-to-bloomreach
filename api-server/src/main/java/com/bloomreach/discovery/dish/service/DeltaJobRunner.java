// api-server/src/main/java/com/bloomreach/discovery/dish/service/DeltaJobRunner.java
package com.bloomreach.discovery.dish.service;

import com.bloomreach.discovery.dish.dto.DeltaScheduleDTO;
import com.bloomreach.discovery.dish.dto.DishConfigDTO;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.Instant;
import java.time.format.DateTimeFormatter;

@Service
@Slf4j
public class DeltaJobRunner {

    private final DockerService dockerService;
    private final DeltaJobTracker deltaJobTracker;

    public DeltaJobRunner(DockerService dockerService, DeltaJobTracker deltaJobTracker) {
        this.dockerService = dockerService;
        this.deltaJobTracker = deltaJobTracker;
    }


    public void runDeltaJob(DeltaScheduleDTO config) {
        String catalogKey = config.getCatalogKey();

        log.info("Starting delta job for catalog: {}", catalogKey);

        if (deltaJobTracker.isJobRunning(catalogKey)) {
            log.warn("Delta job for catalog {} is already running, skipping this execution", catalogKey);
            return;
        }

        try {
            deltaJobTracker.setJobRunning(catalogKey, true);

            // Calculate start date in UTC
            Instant startDate = calculateStartDate(catalogKey, config.deltaInterval().getIntervalMinutes());
            Instant jobStartTime = Instant.now(); // Capture when job actually starts

            log.info("Running delta job for catalog: {} with start date: {}", catalogKey, startDate);

            DishConfigDTO dishConfig = convertToDishConfig(config, startDate);
            String jobName = dockerService.createDeltaContainer(dishConfig, startDate);

            log.info("Delta job container created: {} for catalog: {}", jobName, catalogKey);

            // Update last successful run to the job start time (not current time)
            // This prevents the time window from advancing until the job actually starts
            deltaJobTracker.updateLastSuccessfulRun(catalogKey, jobStartTime);

            log.info("Updated last successful run time to job start time: {}", jobStartTime);

        } catch (Exception e) {
            log.error("Failed to run delta job for catalog: {}", catalogKey, e);
            // Mark job as not running on failure
            deltaJobTracker.setJobRunning(catalogKey, false);
        }
    }

    private Instant calculateStartDate(String catalogKey, int intervalMinutes) {
        Instant lastRun = deltaJobTracker.getLastSuccessfulRun(catalogKey);
        Instant now = Instant.now(); // This is always UTC

        log.info("Current UTC time: {}", now);

        if (lastRun == null) {
            // First run: use current time minus interval minus 30 seconds overlap
            Instant calculated = now.minusSeconds(intervalMinutes * 60L + 30);
            log.info("First run - calculated start date: {}", calculated);
            return calculated;
        } else {
            // Subsequent runs: use last successful run minus 30 seconds overlap
            Instant calculated = lastRun.minusSeconds(30);
            log.info("Subsequent run - last successful: {}, calculated start date: {}", lastRun, calculated);
            return calculated;
        }
    }

    private DishConfigDTO convertToDishConfig(DeltaScheduleDTO deltaConfig, Instant startDate) {
        return new DishConfigDTO(
                deltaConfig.shopifyUrl(),
                deltaConfig.shopifyPat(),
                deltaConfig.brEnvironmentName(),
                deltaConfig.brAccountId(),
                deltaConfig.brCatalogName(),
                deltaConfig.brApiToken(),
                deltaConfig.brMultiMarket(),
                deltaConfig.autoIndex(),
                deltaConfig.shopifyMarket(),
                deltaConfig.shopifyLanguage()
        );
    }
}