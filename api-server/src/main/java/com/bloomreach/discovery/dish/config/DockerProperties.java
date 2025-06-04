package com.bloomreach.discovery.dish.config;

import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Component
@ConfigurationProperties(prefix = "docker")
@Getter
@Setter
public class DockerProperties {
    private String imageTag = "dish-job:latest";
    private String exportPath = "/export";
    private int maxConnections = 20;
    private int connectionTimeout = 30;
    private int responseTimeout = 45;
    private int logTimeout = 3000;
    private String hostPath;
    private int containerRetentionDays = 20; // Default to 20 days retention

}