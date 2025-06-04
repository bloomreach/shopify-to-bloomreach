package com.bloomreach.discovery.dish.util;

import com.github.dockerjava.api.async.ResultCallback;
import com.github.dockerjava.api.model.Frame;

import java.nio.charset.StandardCharsets;

public class LogContainerCallback extends ResultCallback.Adapter<Frame> {
    private final StringBuilder log = new StringBuilder();

    @Override
    public void onNext(Frame frame) {
        if (frame != null && frame.getPayload() != null) {
            log.append(new String(frame.getPayload(), StandardCharsets.UTF_8));
        }
    }

    @Override
    public String toString() {
        return log.toString();
    }
}