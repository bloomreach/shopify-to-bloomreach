package com.bloomreach.discovery.dish.controller;

import com.bloomreach.discovery.dish.dto.DishConfigDTO;
import com.bloomreach.discovery.dish.dto.ErrorResponse;
import com.bloomreach.discovery.dish.dto.JobDTO;
import com.bloomreach.discovery.dish.dto.JobStatus;
import com.bloomreach.discovery.dish.exception.DockerServiceException;
import com.bloomreach.discovery.dish.service.DockerService;
import com.github.dockerjava.api.exception.NotFoundException;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import jakarta.validation.Valid;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.tags.Tag;

import java.util.List;

@RestController
@RequestMapping("/dish")
@Tag(name = "DiSh Operations", description = "API endpoints for managing DiSh jobs")
@Slf4j
public class DishController {

    private final DockerService dockerService;

    public DishController(DockerService dockerService) {
        this.dockerService = dockerService;
    }

    @Operation(
            summary = "Create a new job",
            description = "Creates a new Docker container for processing Shopify data"
    )
    @ApiResponse(responseCode = "201", description = "Job created successfully")
    @ApiResponse(responseCode = "400", description = "Invalid input parameters")
    @ApiResponse(responseCode = "500", description = "Internal server error")
    @PostMapping("/createJob")
    public ResponseEntity<JobDTO> createJob(@Valid @RequestBody DishConfigDTO configRequest) {
        String name = dockerService.createContainer(configRequest);
        return new ResponseEntity<>(new JobDTO(name, JobStatus.CREATED, null), HttpStatus.CREATED);
    }

    @Operation(
            summary = "Get job status",
            description = "Retrieves the current status of a job by its name. Optionally can delete successful jobs and include verbose logs."
    )
    @ApiResponses(value = {
            @ApiResponse(responseCode = "200", description = "Job status retrieved successfully"),
            @ApiResponse(responseCode = "404", description = "Job not found", content = @Content(
                    mediaType = "application/json",
                    schema = @Schema(implementation = ErrorResponse.class)
            )),
            @ApiResponse(responseCode = "500", description = "Internal server error", content = @Content(
                    mediaType = "application/json",
                    schema = @Schema(implementation = ErrorResponse.class)
            ))
    })
    @GetMapping("/statusJob")
    public ResponseEntity<JobDTO> statusJob(
            @Parameter(description = "Name of the job to check status for", required = true)
            @RequestParam String jobName,
            @Parameter(description = "Whether to delete the job if it completed successfully")
            @RequestParam(defaultValue = "false") boolean deleteOnSuccess,
            @Parameter(description = "Whether to include detailed logs in the response")
            @RequestParam(defaultValue = "false") boolean verbose) {
        log.debug("Checking status for job: {}, deleteOnSuccess: {}, verbose: {}",
                jobName, deleteOnSuccess, verbose);

        try {
            JobDTO job = dockerService.getJobStatus(jobName, deleteOnSuccess, verbose);
            log.debug("Retrieved status for job {}: {}", jobName, job.jobStatus());
            return ResponseEntity.ok(job);
        } catch (NotFoundException e) {
            log.warn("Job not found: {}", jobName);
            throw e;
        } catch (Exception e) {
            log.error("Error retrieving status for job: {}", jobName, e);
            throw new DockerServiceException("Failed to retrieve job status", e);
        }
    }

    @GetMapping("/statusJobs")
    public ResponseEntity<List<JobDTO>> statusJobs(
            @Parameter(description = "Names of the jobs to check status for", required = true)
            @RequestParam List<String> jobNames, @Parameter(description = "Whether to include detailed logs in the response for FAILED jobs")
            @RequestParam(defaultValue = "false") boolean verboseOnFailure) {
        log.debug("Checking status for jobs: {}", jobNames);
        try {
            List<JobDTO> jobs = dockerService.getJobStatuses(jobNames, verboseOnFailure);
            log.debug("Retrieved statuses for {} jobs", jobs.size());
            return ResponseEntity.ok(jobs);
        } catch (Exception e) {
            log.error("Error retrieving statuses for jobs", e);
            throw new DockerServiceException("Failed to retrieve job statuses", e);
        }
    }

}
