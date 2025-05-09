// Create a new file: com/bloomreach/discovery/dish/service/ContainerCleanupService.java

package com.bloomreach.discovery.dish.service;

import com.bloomreach.discovery.dish.config.DockerProperties;
import com.bloomreach.discovery.dish.exception.DockerServiceException;
import com.github.dockerjava.api.DockerClient;
import com.github.dockerjava.api.model.Container;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.List;

@Service
public class ContainerCleanupService {

    private static final Logger log = LoggerFactory.getLogger(ContainerCleanupService.class);
    private final DockerClient dockerClient;
    private final DockerProperties properties;

    public ContainerCleanupService(DockerClient dockerClient, DockerProperties properties) {
        this.dockerClient = dockerClient;
        this.properties = properties;
    }

    /**
     * Scheduled job that runs daily to clean up old containers
     * Containers that match our dish- prefix and are older than the retention period will be removed
     */
    @Scheduled(cron = "${dish.container.cleanup.cron:0 0 2 * * ?}") // Default: Run at 2 AM every day
    public void cleanupOldContainers() {
        log.info("Starting scheduled cleanup of old containers");
        try {
            int retentionDays = properties.getContainerRetentionDays();
            log.debug("Container retention period set to {} days", retentionDays);
            
            if (retentionDays <= 0) {
                log.info("Container cleanup disabled (retention days <= 0)");
                return;
            }

            // Calculate cutoff timestamp
            long cutoffTimestamp = Instant.now().minus(retentionDays, ChronoUnit.DAYS).toEpochMilli() / 1000;
            log.debug("Removing containers created before: {}", Instant.ofEpochSecond(cutoffTimestamp));

            // Get all containers, including stopped ones
            List<Container> containers = dockerClient.listContainersCmd()
                    .withShowAll(true)
                    .exec();
            
            int removedCount = 0;
            for (Container container : containers) {
                // Only process our DiSh containers by checking name prefix
                String containerName = container.getNames()[0].substring(1); // Remove leading slash
                
                // Skip the main application container "dish-app" and only clean job containers
                if (containerName.startsWith("dish-") && !containerName.equals("dish-app") && 
                    container.getCreated() < cutoffTimestamp) {
                    try {
                        log.info("Removing old container: {} (created: {})", 
                                containerName, Instant.ofEpochSecond(container.getCreated()));
                        dockerClient.removeContainerCmd(container.getId()).exec();
                        removedCount++;
                    } catch (Exception e) {
                        log.warn("Failed to remove container {}: {}", containerName, e.getMessage());
                    }
                }
            }
            
            log.info("Container cleanup completed. Removed {} containers", removedCount);
        } catch (Exception e) {
            log.error("Error during container cleanup", e);
            throw new DockerServiceException("Container cleanup failed", e);
        }
    }
    
    /**
     * Manual trigger for container cleanup with custom retention period
     * 
     * @param days Number of days to retain containers
     * @return Number of containers removed
     */
    public int manualCleanup(int days) {
        log.info("Starting manual cleanup of containers older than {} days", days);
        try {
            if (days <= 0) {
                throw new IllegalArgumentException("Retention days must be greater than 0");
            }

            // Calculate cutoff timestamp
            long cutoffTimestamp = Instant.now().minus(days, ChronoUnit.DAYS).toEpochMilli() / 1000;
            
            // Get all containers, including stopped ones
            List<Container> containers = dockerClient.listContainersCmd()
                    .withShowAll(true)
                    .exec();
            
            int removedCount = 0;
            for (Container container : containers) {
                // Only process our DiSh containers
                String containerName = container.getNames()[0].substring(1); // Remove leading slash
                
                // Skip the main application container "dish-app" and only clean job containers
                if (containerName.startsWith("dish-") && !containerName.equals("dish-app") && 
                    container.getCreated() < cutoffTimestamp) {
                    try {
                        log.info("Removing old container: {}", containerName);
                        dockerClient.removeContainerCmd(container.getId()).exec();
                        removedCount++;
                    } catch (Exception e) {
                        log.warn("Failed to remove container {}: {}", containerName, e.getMessage());
                    }
                }
            }
            
            log.info("Manual container cleanup completed. Removed {} containers", removedCount);
            return removedCount;
        } catch (Exception e) {
            log.error("Error during manual container cleanup", e);
            throw new DockerServiceException("Manual container cleanup failed", e);
        }
    }
}