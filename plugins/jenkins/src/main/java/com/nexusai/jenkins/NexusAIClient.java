package com.nexusai.jenkins;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import org.apache.http.client.methods.CloseableHttpResponse;
import org.apache.http.client.methods.HttpGet;
import org.apache.http.client.methods.HttpPost;
import org.apache.http.entity.StringEntity;
import org.apache.http.impl.client.CloseableHttpClient;
import org.apache.http.impl.client.HttpClients;
import org.apache.http.util.EntityUtils;

import java.io.IOException;
import java.io.Serializable;
import java.util.List;
import java.util.Map;

/**
 * HTTP client for NexusAI API communication.
 */
public class NexusAIClient implements Serializable {
    private static final long serialVersionUID = 1L;
    
    private final String apiEndpoint;
    private final String apiToken;
    private final Gson gson = new Gson();

    public NexusAIClient(String apiEndpoint, String apiToken) {
        this.apiEndpoint = apiEndpoint.endsWith("/") ? apiEndpoint.substring(0, apiEndpoint.length() - 1) : apiEndpoint;
        this.apiToken = apiToken;
    }

    /**
     * Test API connection.
     */
    public boolean testConnection() throws IOException {
        try (CloseableHttpClient client = HttpClients.createDefault()) {
            HttpGet request = new HttpGet(apiEndpoint + "/api/v2/health");
            request.addHeader("Authorization", "Bearer " + apiToken);
            
            try (CloseableHttpResponse response = client.execute(request)) {
                return response.getStatusLine().getStatusCode() == 200;
            }
        }
    }

    /**
     * Analyze build results.
     */
    public AnalysisResult analyzeBuild(BuildContext context) throws IOException {
        JsonObject payload = new JsonObject();
        payload.addProperty("job_name", context.getJobName());
        payload.addProperty("build_number", context.getBuildNumber());
        payload.addProperty("status", context.getStatus());
        payload.addProperty("duration_ms", context.getDurationMs());
        
        if (context.getLog() != null) {
            payload.addProperty("log", context.getLog());
        }
        if (context.getChanges() != null) {
            payload.add("changes", gson.toJsonTree(context.getChanges()));
        }
        
        String response = post("/api/v2/ci/analyze", payload);
        return gson.fromJson(response, AnalysisResult.class);
    }

    /**
     * Run quality gate check.
     */
    public QualityGateResult checkQualityGate(QualityGateRequest request) throws IOException {
        JsonObject payload = new JsonObject();
        payload.addProperty("threshold", request.getThreshold());
        payload.addProperty("fail_on_issues", request.isFailOnIssues());
        
        if (request.getCategories() != null) {
            payload.add("categories", gson.toJsonTree(request.getCategories()));
        }
        if (request.getCode() != null) {
            payload.addProperty("code", request.getCode());
        }
        
        String response = post("/api/v2/ci/quality-gate", payload);
        return gson.fromJson(response, QualityGateResult.class);
    }

    /**
     * Review pull request.
     */
    public PRReviewResult reviewPullRequest(String repo, int prNumber, String diff) throws IOException {
        JsonObject payload = new JsonObject();
        payload.addProperty("repo", repo);
        payload.addProperty("pr_number", prNumber);
        payload.addProperty("diff", diff);
        
        String response = post("/api/v2/pr/review", payload);
        return gson.fromJson(response, PRReviewResult.class);
    }

    /**
     * Send notification.
     */
    public void sendNotification(NotificationRequest request) throws IOException {
        JsonObject payload = new JsonObject();
        payload.addProperty("channel", request.getChannel());
        payload.addProperty("message", request.getMessage());
        payload.addProperty("include_analysis", request.isIncludeAnalysis());
        
        if (request.getMentionOnFailure() != null) {
            payload.addProperty("mention_on_failure", request.getMentionOnFailure());
        }
        
        post("/api/v2/notify", payload);
    }

    /**
     * Report metrics.
     */
    public void reportMetrics(MetricsReport report) throws IOException {
        JsonObject payload = gson.toJsonTree(report).getAsJsonObject();
        post("/api/v2/metrics/report", payload);
    }

    private String post(String endpoint, JsonObject payload) throws IOException {
        try (CloseableHttpClient client = HttpClients.createDefault()) {
            HttpPost request = new HttpPost(apiEndpoint + endpoint);
            request.addHeader("Authorization", "Bearer " + apiToken);
            request.addHeader("Content-Type", "application/json");
            request.addHeader("X-Client", "jenkins-plugin");
            request.setEntity(new StringEntity(gson.toJson(payload)));
            
            try (CloseableHttpResponse response = client.execute(request)) {
                int statusCode = response.getStatusLine().getStatusCode();
                String body = EntityUtils.toString(response.getEntity());
                
                if (statusCode >= 400) {
                    throw new IOException("API request failed: " + statusCode + " - " + body);
                }
                
                return body;
            }
        }
    }

    // Data classes

    public static class BuildContext implements Serializable {
        private static final long serialVersionUID = 1L;
        
        private String jobName;
        private int buildNumber;
        private String status;
        private long durationMs;
        private String log;
        private List<Map<String, String>> changes;

        // Getters and setters
        public String getJobName() { return jobName; }
        public void setJobName(String jobName) { this.jobName = jobName; }
        public int getBuildNumber() { return buildNumber; }
        public void setBuildNumber(int buildNumber) { this.buildNumber = buildNumber; }
        public String getStatus() { return status; }
        public void setStatus(String status) { this.status = status; }
        public long getDurationMs() { return durationMs; }
        public void setDurationMs(long durationMs) { this.durationMs = durationMs; }
        public String getLog() { return log; }
        public void setLog(String log) { this.log = log; }
        public List<Map<String, String>> getChanges() { return changes; }
        public void setChanges(List<Map<String, String>> changes) { this.changes = changes; }
    }

    public static class AnalysisResult implements Serializable {
        private static final long serialVersionUID = 1L;
        
        private String summary;
        private String rootCause;
        private List<String> suggestions;
        private String severity;
        private Map<String, Object> metrics;

        public String getSummary() { return summary; }
        public String getRootCause() { return rootCause; }
        public List<String> getSuggestions() { return suggestions; }
        public String getSeverity() { return severity; }
        public Map<String, Object> getMetrics() { return metrics; }
    }

    public static class QualityGateRequest implements Serializable {
        private static final long serialVersionUID = 1L;
        
        private String threshold;
        private boolean failOnIssues;
        private List<String> categories;
        private String code;

        public String getThreshold() { return threshold; }
        public void setThreshold(String threshold) { this.threshold = threshold; }
        public boolean isFailOnIssues() { return failOnIssues; }
        public void setFailOnIssues(boolean failOnIssues) { this.failOnIssues = failOnIssues; }
        public List<String> getCategories() { return categories; }
        public void setCategories(List<String> categories) { this.categories = categories; }
        public String getCode() { return code; }
        public void setCode(String code) { this.code = code; }
    }

    public static class QualityGateResult implements Serializable {
        private static final long serialVersionUID = 1L;
        
        private boolean passed;
        private String status;
        private List<Issue> issues;
        private int score;

        public boolean isPassed() { return passed; }
        public String getStatus() { return status; }
        public List<Issue> getIssues() { return issues; }
        public int getScore() { return score; }
    }

    public static class Issue implements Serializable {
        private static final long serialVersionUID = 1L;
        
        private String type;
        private String severity;
        private String message;
        private String file;
        private int line;

        public String getType() { return type; }
        public String getSeverity() { return severity; }
        public String getMessage() { return message; }
        public String getFile() { return file; }
        public int getLine() { return line; }
    }

    public static class PRReviewResult implements Serializable {
        private static final long serialVersionUID = 1L;
        
        private String summary;
        private String riskLevel;
        private List<PRComment> comments;
        private String approvalRecommendation;

        public String getSummary() { return summary; }
        public String getRiskLevel() { return riskLevel; }
        public List<PRComment> getComments() { return comments; }
        public String getApprovalRecommendation() { return approvalRecommendation; }
    }

    public static class PRComment implements Serializable {
        private static final long serialVersionUID = 1L;
        
        private String path;
        private int line;
        private String body;
        private String severity;

        public String getPath() { return path; }
        public int getLine() { return line; }
        public String getBody() { return body; }
        public String getSeverity() { return severity; }
    }

    public static class NotificationRequest implements Serializable {
        private static final long serialVersionUID = 1L;
        
        private String channel;
        private String message;
        private boolean includeAnalysis;
        private String mentionOnFailure;

        public String getChannel() { return channel; }
        public void setChannel(String channel) { this.channel = channel; }
        public String getMessage() { return message; }
        public void setMessage(String message) { this.message = message; }
        public boolean isIncludeAnalysis() { return includeAnalysis; }
        public void setIncludeAnalysis(boolean includeAnalysis) { this.includeAnalysis = includeAnalysis; }
        public String getMentionOnFailure() { return mentionOnFailure; }
        public void setMentionOnFailure(String mentionOnFailure) { this.mentionOnFailure = mentionOnFailure; }
    }

    public static class MetricsReport implements Serializable {
        private static final long serialVersionUID = 1L;
        
        private String jobName;
        private int buildNumber;
        private String status;
        private long durationMs;
        private long queueTimeMs;
        private Map<String, Object> customMetrics;

        public String getJobName() { return jobName; }
        public void setJobName(String jobName) { this.jobName = jobName; }
        public int getBuildNumber() { return buildNumber; }
        public void setBuildNumber(int buildNumber) { this.buildNumber = buildNumber; }
        public String getStatus() { return status; }
        public void setStatus(String status) { this.status = status; }
        public long getDurationMs() { return durationMs; }
        public void setDurationMs(long durationMs) { this.durationMs = durationMs; }
        public long getQueueTimeMs() { return queueTimeMs; }
        public void setQueueTimeMs(long queueTimeMs) { this.queueTimeMs = queueTimeMs; }
        public Map<String, Object> getCustomMetrics() { return customMetrics; }
        public void setCustomMetrics(Map<String, Object> customMetrics) { this.customMetrics = customMetrics; }
    }
}
