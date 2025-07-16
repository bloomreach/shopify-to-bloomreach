// api-server/src/main/java/com/bloomreach/discovery/dish/service/DeltaTaskManager.java
package com.bloomreach.discovery.dish.service;

import com.bloomreach.discovery.dish.dto.DeltaScheduleDTO;
import com.bloomreach.discovery.dish.dto.DeltaTaskInfo;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.TaskScheduler;
import org.springframework.scheduling.support.CronTrigger;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ScheduledFuture;

@Service
@Slf4j
public class DeltaTaskManager {

    private final TaskScheduler taskScheduler;
    private final DeltaJobRunner deltaJobRunner;
    private final Map<String, ScheduledTask> activeTasks = new ConcurrentHashMap<>();

    public DeltaTaskManager(TaskScheduler taskScheduler, DeltaJobRunner deltaJobRunner) {
        this.taskScheduler = taskScheduler;
        this.deltaJobRunner = deltaJobRunner;
    }

    private static class ScheduledTask {
        final String taskId;
        final DeltaScheduleDTO config;
        final ScheduledFuture<?> future;
        final LocalDateTime createdAt;

        ScheduledTask(String taskId, DeltaScheduleDTO config, ScheduledFuture<?> future) {
            this.taskId = taskId;
            this.config = config;
            this.future = future;
            this.createdAt = LocalDateTime.now();
        }
    }

    public String scheduleDeltaJob(DeltaScheduleDTO config) {
        String taskId = UUID.randomUUID().toString();
        String catalogKey = config.getCatalogKey();

        log.info("Scheduling delta job for catalog: {}, interval: {}", catalogKey, config.deltaInterval());

        Runnable task = () -> deltaJobRunner.runDeltaJob(config);
        
        ScheduledFuture<?> future = taskScheduler.schedule(task, new CronTrigger(config.deltaInterval().getCronExpression()));
        
        activeTasks.put(taskId, new ScheduledTask(taskId, config, future));
        
        log.info("Delta job scheduled with task ID: {}", taskId);
        return taskId;
    }

    public boolean cancelDeltaJob(String taskId) {
        ScheduledTask task = activeTasks.remove(taskId);
        if (task != null) {
            boolean cancelled = task.future.cancel(false);
            log.info("Delta job {} cancelled: {}", taskId, cancelled);
            return cancelled;
        }
        return false;
    }

    public List<DeltaTaskInfo> getActiveTasks() {
        return activeTasks.values().stream()
                .map(task -> new DeltaTaskInfo(
                        task.taskId,
                        task.config.getCatalogKey(),
                        task.config.deltaInterval(),
                        task.createdAt,
                        null, // We don't track last run here, could be enhanced
                        false // We don't track running status here, could be enhanced
                ))
                .toList();
    }
}