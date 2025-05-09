package com.bloomreach.discovery.dish.dto;

public record JobDTO(
        String jobName,
        JobStatus jobStatus,
        String jobLog
) {
    // Validate that jobName is not null or empty
    public JobDTO {
        if (jobName == null || jobName.trim().isEmpty()) {
            throw new IllegalArgumentException("Job name cannot be null or empty");
        }
        // jobStatus can be null when a container is not found
//        if (jobStatus == null) {
//            throw new IllegalArgumentException("Job status cannot be null");
//        }
        // jobLog can be null as it might be empty initially
    }


}