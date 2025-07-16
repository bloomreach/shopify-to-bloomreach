// api-server/src/main/java/com/bloomreach/discovery/dish/dto/DeltaTaskInfo.java
package com.bloomreach.discovery.dish.dto;

import java.time.LocalDateTime;

public record DeltaTaskInfo(
        String taskId,
        String catalogKey,
        DeltaInterval interval,
        LocalDateTime createdAt,
        LocalDateTime lastRun,
        boolean isRunning
) {}