// api-server/src/main/java/com/bloomreach/discovery/dish/dto/DeltaTaskInfo.java
package com.bloomreach.discovery.dish.dto;

public record DeltaTaskInfo(
        String taskId,
        String catalogKey,
        DeltaInterval interval
) {}