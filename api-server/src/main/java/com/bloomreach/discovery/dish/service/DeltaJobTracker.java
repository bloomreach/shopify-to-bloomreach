// api-server/src/main/java/com/bloomreach/discovery/dish/service/DeltaJobTracker.java
package com.bloomreach.discovery.dish.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.File;
import java.io.IOException;
import java.time.Instant;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.locks.ReadWriteLock;
import java.util.concurrent.locks.ReentrantReadWriteLock;

@Service
@Slf4j
public class DeltaJobTracker {

    private final String filePath;
    private final ObjectMapper objectMapper;
    private final ReadWriteLock lock = new ReentrantReadWriteLock();

    public DeltaJobTracker(@Value("${dish.delta.tracker.file:./delta-job-tracker.json}") String filePath) {
        this.filePath = filePath;
        this.objectMapper = new ObjectMapper();
        this.objectMapper.registerModule(new JavaTimeModule());
    }

    public static class JobInfo {
        public Instant lastSuccessfulRun;
        
        public JobInfo() {}
        
        public JobInfo(Instant lastSuccessfulRun) {
            this.lastSuccessfulRun = lastSuccessfulRun;
        }
    }

    private Map<String, JobInfo> loadData() {
        lock.readLock().lock();
        try {
            File file = new File(filePath);
            if (!file.exists()) {
                return new HashMap<>();
            }
            
            @SuppressWarnings("unchecked")
            Map<String, JobInfo> data = objectMapper.readValue(file, 
                objectMapper.getTypeFactory().constructMapType(HashMap.class, String.class, JobInfo.class));
            return data;
        } catch (IOException e) {
            log.error("Failed to load delta job tracker data", e);
            return new HashMap<>();
        } finally {
            lock.readLock().unlock();
        }
    }

    private void saveData(Map<String, JobInfo> data) {
        lock.writeLock().lock();
        try {
            objectMapper.writeValue(new File(filePath), data);
        } catch (IOException e) {
            log.error("Failed to save delta job tracker data", e);
        } finally {
            lock.writeLock().unlock();
        }
    }

    public Instant getLastSuccessfulRun(String catalogKey) {
        Map<String, JobInfo> data = loadData();
        JobInfo info = data.get(catalogKey);
        return info != null ? info.lastSuccessfulRun : null;
    }

    public void updateLastSuccessfulRun(String catalogKey, Instant timestamp) {
        Map<String, JobInfo> data = loadData();
        JobInfo info = data.computeIfAbsent(catalogKey, k -> new JobInfo());
        info.lastSuccessfulRun = timestamp;
        data.put(catalogKey, info);
        saveData(data);
        log.debug("Updated last successful run for catalog {}: {}", catalogKey, timestamp);
    }
}