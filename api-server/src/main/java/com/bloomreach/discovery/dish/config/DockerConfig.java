package com.bloomreach.discovery.dish.config;

import com.github.dockerjava.api.DockerClient;
import com.github.dockerjava.core.DefaultDockerClientConfig;
import com.github.dockerjava.core.DockerClientConfig;
import com.github.dockerjava.core.DockerClientImpl;
import com.github.dockerjava.zerodep.ZerodepDockerHttpClient;
import com.github.dockerjava.transport.DockerHttpClient;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.time.Duration;

@Configuration
public class DockerConfig {
    private final DockerProperties properties;

    public DockerConfig(DockerProperties properties) {
        this.properties = properties;
    }

    @Bean
    public DockerClient dockerClient() {
        DockerClientConfig config = DefaultDockerClientConfig.createDefaultConfigBuilder()
                .build();

        DockerHttpClient httpClient = new ZerodepDockerHttpClient.Builder()
                .dockerHost(config.getDockerHost())
                .maxConnections(properties.getMaxConnections())
                .connectionTimeout(Duration.ofSeconds(properties.getConnectionTimeout()))
                .responseTimeout(Duration.ofSeconds(properties.getResponseTimeout()))
                .build();

        return DockerClientImpl.getInstance(config, httpClient);
    }
}