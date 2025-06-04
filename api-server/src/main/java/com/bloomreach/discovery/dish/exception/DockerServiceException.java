package com.bloomreach.discovery.dish.exception;

public class DockerServiceException extends RuntimeException {
    public DockerServiceException(String message, Throwable cause) {
        super(message, cause);
    }
}