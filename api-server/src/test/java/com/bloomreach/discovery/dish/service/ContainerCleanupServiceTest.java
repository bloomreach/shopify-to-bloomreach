package com.bloomreach.discovery.dish.service;

import org.junit.jupiter.api.Disabled;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

@Disabled
@SpringBootTest
class ContainerCleanupServiceTest {

    @Autowired
    private ContainerCleanupService containerCleanupService;

    @Test
    void cleanupOldContainers() {
    }

    @Test
    void manualCleanup() {
        int amount = containerCleanupService.manualCleanup(2);
        System.out.println(amount);
    }
}