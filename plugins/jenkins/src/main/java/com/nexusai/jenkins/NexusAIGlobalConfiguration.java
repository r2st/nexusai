package com.nexusai.jenkins;

import hudson.Extension;
import hudson.util.FormValidation;
import hudson.util.Secret;
import jenkins.model.GlobalConfiguration;
import org.kohsuke.stapler.DataBoundSetter;
import org.kohsuke.stapler.QueryParameter;
import org.kohsuke.stapler.verb.POST;

/**
 * Global configuration for NexusAI plugin.
 */
@Extension
public class NexusAIGlobalConfiguration extends GlobalConfiguration {

    private String apiEndpoint = "https://api.nexusai.dev";
    private Secret apiToken;
    private boolean enableTelemetry = true;
    private String defaultThreshold = "medium";

    public NexusAIGlobalConfiguration() {
        load();
    }

    public static NexusAIGlobalConfiguration get() {
        return GlobalConfiguration.all().get(NexusAIGlobalConfiguration.class);
    }

    public String getApiEndpoint() {
        return apiEndpoint;
    }

    @DataBoundSetter
    public void setApiEndpoint(String apiEndpoint) {
        this.apiEndpoint = apiEndpoint;
        save();
    }

    public Secret getApiToken() {
        return apiToken;
    }

    @DataBoundSetter
    public void setApiToken(Secret apiToken) {
        this.apiToken = apiToken;
        save();
    }

    public boolean isEnableTelemetry() {
        return enableTelemetry;
    }

    @DataBoundSetter
    public void setEnableTelemetry(boolean enableTelemetry) {
        this.enableTelemetry = enableTelemetry;
        save();
    }

    public String getDefaultThreshold() {
        return defaultThreshold;
    }

    @DataBoundSetter
    public void setDefaultThreshold(String defaultThreshold) {
        this.defaultThreshold = defaultThreshold;
        save();
    }

    @POST
    public FormValidation doCheckApiEndpoint(@QueryParameter String value) {
        if (value == null || value.isEmpty()) {
            return FormValidation.error("API endpoint is required");
        }
        if (!value.startsWith("https://")) {
            return FormValidation.warning("Using non-HTTPS endpoint is not recommended");
        }
        return FormValidation.ok();
    }

    @POST
    public FormValidation doTestConnection(
            @QueryParameter("apiEndpoint") String apiEndpoint,
            @QueryParameter("apiToken") Secret apiToken) {
        
        if (apiEndpoint == null || apiEndpoint.isEmpty()) {
            return FormValidation.error("API endpoint is required");
        }
        if (apiToken == null || apiToken.getPlainText().isEmpty()) {
            return FormValidation.error("API token is required");
        }

        try {
            NexusAIClient client = new NexusAIClient(apiEndpoint, apiToken.getPlainText());
            if (client.testConnection()) {
                return FormValidation.ok("Connection successful!");
            } else {
                return FormValidation.error("Connection failed");
            }
        } catch (Exception e) {
            return FormValidation.error("Connection failed: " + e.getMessage());
        }
    }
}
