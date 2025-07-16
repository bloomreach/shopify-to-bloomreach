// api-server/src/main/java/com/bloomreach/discovery/dish/dto/DeltaInterval.java
package com.bloomreach.discovery.dish.dto;

public enum DeltaInterval {
    EVERY_2_MINUTES("0 */2 * * * *", 2),
    EVERY_5_MINUTES("0 */5 * * * *", 5),
    EVERY_15_MINUTES("0 */15 * * * *", 15),
    EVERY_30_MINUTES("0 */30 * * * *", 30),
    EVERY_HOUR("0 0 * * * *", 60),
    EVERY_2_HOURS("0 0 */2 * * *", 120),
    EVERY_6_HOURS("0 0 */6 * * *", 360),
    EVERY_12_HOURS("0 0 */12 * * *", 720);

    private final String cronExpression;
    private final int intervalMinutes;

    DeltaInterval(String cronExpression, int intervalMinutes) {
        this.cronExpression = cronExpression;
        this.intervalMinutes = intervalMinutes;
    }

    public String getCronExpression() {
        return cronExpression;
    }

    public int getIntervalMinutes() {
        return intervalMinutes;
    }
}