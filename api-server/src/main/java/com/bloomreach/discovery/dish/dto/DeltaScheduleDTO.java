// api-server/src/main/java/com/bloomreach/discovery/dish/dto/DeltaScheduleDTO.java
package com.bloomreach.discovery.dish.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;

public record DeltaScheduleDTO(
        @NotBlank(message = "Shopify URL is required")
        String shopifyUrl,

        @NotBlank(message = "Shopify PAT token is required")
        String shopifyPat,

        @NotBlank(message = "Bloomreach environment is required")
        String brEnvironmentName,

        @NotBlank(message = "Bloomreach account ID is required")
        String brAccountId,

        @NotBlank(message = "Bloomreach catalog name is required")
        String brCatalogName,

        @NotBlank(message = "Bloomreach API token is required")
        String brApiToken,

        boolean brMultiMarket,

        boolean autoIndex,

        String shopifyMarket,

        @Pattern(regexp = "^[a-z]{2}(-[A-Z]{2})?$", message = "Invalid language format. Must be ISO format like 'en' or 'en-US'")
        String shopifyLanguage,

        @NotNull(message = "Delta interval is required")
        DeltaInterval deltaInterval
) {
    public DeltaScheduleDTO {
        if (brMultiMarket) {
            if (shopifyMarket == null || shopifyMarket.trim().isEmpty()) {
                throw new IllegalArgumentException("Shopify market is required when multi-market is enabled");
            }
            if (shopifyLanguage == null || shopifyLanguage.trim().isEmpty()) {
                throw new IllegalArgumentException("Shopify language is required when multi-market is enabled");
            }
        }
    }

    public String getCatalogKey() {
        return String.format("%s-%s-%s-%s", shopifyUrl, brCatalogName, brAccountId, brEnvironmentName);
    }
}