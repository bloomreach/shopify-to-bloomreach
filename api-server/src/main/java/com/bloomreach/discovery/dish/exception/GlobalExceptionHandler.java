package com.bloomreach.discovery.dish.exception;

import com.bloomreach.discovery.dish.dto.ErrorResponse;
import com.github.dockerjava.api.exception.NotFoundException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ExceptionHandler;

import java.util.Objects;

@ControllerAdvice
public class GlobalExceptionHandler {
    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<ErrorResponse> handleIllegalArgumentException(IllegalArgumentException ex) {
        log.error("Validation error:", ex);
        return new ResponseEntity<>(
                new ErrorResponse(ex.getMessage(), "VALIDATION_ERROR"),
                HttpStatus.BAD_REQUEST
        );
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorResponse> handleValidationException(MethodArgumentNotValidException ex) {
        log.error("Validation error:", ex);
        String errorMessage = ex.getBindingResult().getAllErrors().stream()
                .map(error -> {
                    if (Objects.requireNonNull(error.getDefaultMessage()).contains("shopifyMarket") ||
                            error.getDefaultMessage().contains("shopifyLanguage")) {
                        // Add context about multi-market requirement
                        return error.getDefaultMessage() + " (required for multi-market)";
                    }
                    return error.getDefaultMessage();
                })
                .reduce((a, b) -> a + "; " + b)
                .orElse("Validation failed");

        return new ResponseEntity<>(
                new ErrorResponse(errorMessage, "VALIDATION_ERROR"),
                HttpStatus.BAD_REQUEST
        );
    }

    @ExceptionHandler(DockerServiceException.class)
    public ResponseEntity<ErrorResponse> handleDockerServiceException(DockerServiceException ex) {
        log.error("Docker service error:", ex);
        return new ResponseEntity<>(
            new ErrorResponse(ex.getMessage(), "DOCKER_SERVICE_ERROR"),
            HttpStatus.INTERNAL_SERVER_ERROR
        );
    }

    @ExceptionHandler(NotFoundException.class)
    public ResponseEntity<ErrorResponse> handleNotFoundException(NotFoundException ex) {
        log.error("Resource not found:", ex);
        return new ResponseEntity<>(
            new ErrorResponse("Resource not found", "NOT_FOUND"),
            HttpStatus.NOT_FOUND
        );
    }


    @ExceptionHandler(SecurityException.class)
    public ResponseEntity<ErrorResponse> handleSecurityException(SecurityException ex) {
        return new ResponseEntity<>(
                new ErrorResponse("Access denied", "SECURITY_ERROR"),
                HttpStatus.FORBIDDEN
        );
    }
}