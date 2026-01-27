package com.nexusai.jenkins.steps;

import com.nexusai.jenkins.NexusAIClient;
import com.nexusai.jenkins.NexusAIGlobalConfiguration;
import hudson.AbortException;
import hudson.Extension;
import hudson.model.TaskListener;
import org.jenkinsci.plugins.workflow.steps.*;
import org.kohsuke.stapler.DataBoundConstructor;
import org.kohsuke.stapler.DataBoundSetter;

import javax.annotation.Nonnull;
import java.io.PrintStream;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Set;

/**
 * Pipeline step for NexusAI quality gate.
 * 
 * Usage: nexusaiQualityGate(threshold: 'high', failOnIssues: true)
 */
public class NexusAIQualityGateStep extends Step implements Serializable {
    private static final long serialVersionUID = 1L;
    
    private String threshold = "medium";
    private boolean failOnIssues = true;
    private List<String> categories;

    @DataBoundConstructor
    public NexusAIQualityGateStep() {
    }

    public String getThreshold() {
        return threshold;
    }

    @DataBoundSetter
    public void setThreshold(String threshold) {
        this.threshold = threshold;
    }

    public boolean isFailOnIssues() {
        return failOnIssues;
    }

    @DataBoundSetter
    public void setFailOnIssues(boolean failOnIssues) {
        this.failOnIssues = failOnIssues;
    }

    public List<String> getCategories() {
        return categories;
    }

    @DataBoundSetter
    public void setCategories(List<String> categories) {
        this.categories = categories;
    }

    @Override
    public StepExecution start(StepContext context) throws Exception {
        return new Execution(context, this);
    }

    private static class Execution extends SynchronousNonBlockingStepExecution<NexusAIClient.QualityGateResult> {
        private static final long serialVersionUID = 1L;
        
        private final NexusAIQualityGateStep step;

        Execution(StepContext context, NexusAIQualityGateStep step) {
            super(context);
            this.step = step;
        }

        @Override
        protected NexusAIClient.QualityGateResult run() throws Exception {
            TaskListener listener = getContext().get(TaskListener.class);
            PrintStream logger = listener.getLogger();
            
            logger.println("[NexusAI] Running quality gate check...");
            logger.println("  Threshold: " + step.threshold);
            logger.println("  Fail on issues: " + step.failOnIssues);
            
            NexusAIGlobalConfiguration config = NexusAIGlobalConfiguration.get();
            if (config.getApiToken() == null) {
                throw new IllegalStateException("NexusAI is not configured");
            }
            
            NexusAIClient client = new NexusAIClient(
                config.getApiEndpoint(),
                config.getApiToken().getPlainText()
            );
            
            NexusAIClient.QualityGateRequest request = new NexusAIClient.QualityGateRequest();
            request.setThreshold(step.threshold);
            request.setFailOnIssues(step.failOnIssues);
            request.setCategories(step.categories);
            
            NexusAIClient.QualityGateResult result = client.checkQualityGate(request);
            
            logger.println("[NexusAI] Quality Gate Result:");
            logger.println("  Status: " + result.getStatus());
            logger.println("  Passed: " + result.isPassed());
            logger.println("  Score: " + result.getScore());
            
            if (result.getIssues() != null && !result.getIssues().isEmpty()) {
                logger.println("  Issues found: " + result.getIssues().size());
                for (NexusAIClient.Issue issue : result.getIssues()) {
                    logger.println("    [" + issue.getSeverity() + "] " + issue.getMessage());
                    if (issue.getFile() != null) {
                        logger.println("      at " + issue.getFile() + ":" + issue.getLine());
                    }
                }
            }
            
            if (!result.isPassed() && step.failOnIssues) {
                throw new AbortException("Quality gate failed: " + result.getStatus());
            }
            
            return result;
        }
    }

    @Extension
    public static class DescriptorImpl extends StepDescriptor {
        @Override
        public Set<? extends Class<?>> getRequiredContext() {
            return Collections.singleton(TaskListener.class);
        }

        @Override
        @Nonnull
        public String getFunctionName() {
            return "nexusaiQualityGate";
        }

        @Override
        @Nonnull
        public String getDisplayName() {
            return "NexusAI Quality Gate";
        }
    }
}
