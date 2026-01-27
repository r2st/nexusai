package com.nexusai.jenkins.steps;

import com.nexusai.jenkins.NexusAIClient;
import com.nexusai.jenkins.NexusAIGlobalConfiguration;
import hudson.Extension;
import hudson.model.Run;
import hudson.model.TaskListener;
import org.jenkinsci.plugins.workflow.steps.*;
import org.kohsuke.stapler.DataBoundConstructor;
import org.kohsuke.stapler.DataBoundSetter;

import javax.annotation.Nonnull;
import java.io.PrintStream;
import java.io.Serializable;
import java.util.Collections;
import java.util.Set;

/**
 * Pipeline step for NexusAI build analysis.
 * 
 * Usage: nexusaiAnalyze()
 */
public class NexusAIAnalyzeStep extends Step implements Serializable {
    private static final long serialVersionUID = 1L;
    
    private boolean includeTests = true;
    private boolean includeLogs = true;
    private String depth = "standard";

    @DataBoundConstructor
    public NexusAIAnalyzeStep() {
    }

    public boolean isIncludeTests() {
        return includeTests;
    }

    @DataBoundSetter
    public void setIncludeTests(boolean includeTests) {
        this.includeTests = includeTests;
    }

    public boolean isIncludeLogs() {
        return includeLogs;
    }

    @DataBoundSetter
    public void setIncludeLogs(boolean includeLogs) {
        this.includeLogs = includeLogs;
    }

    public String getDepth() {
        return depth;
    }

    @DataBoundSetter
    public void setDepth(String depth) {
        this.depth = depth;
    }

    @Override
    public StepExecution start(StepContext context) throws Exception {
        return new Execution(context, this);
    }

    private static class Execution extends SynchronousNonBlockingStepExecution<NexusAIClient.AnalysisResult> {
        private static final long serialVersionUID = 1L;
        
        private final NexusAIAnalyzeStep step;

        Execution(StepContext context, NexusAIAnalyzeStep step) {
            super(context);
            this.step = step;
        }

        @Override
        protected NexusAIClient.AnalysisResult run() throws Exception {
            Run<?, ?> run = getContext().get(Run.class);
            TaskListener listener = getContext().get(TaskListener.class);
            PrintStream logger = listener.getLogger();
            
            logger.println("[NexusAI] Starting build analysis...");
            
            NexusAIGlobalConfiguration config = NexusAIGlobalConfiguration.get();
            if (config.getApiToken() == null) {
                throw new IllegalStateException("NexusAI is not configured. Please configure it in Jenkins settings.");
            }
            
            NexusAIClient client = new NexusAIClient(
                config.getApiEndpoint(),
                config.getApiToken().getPlainText()
            );
            
            // Build context
            NexusAIClient.BuildContext context = new NexusAIClient.BuildContext();
            context.setJobName(run.getParent().getFullName());
            context.setBuildNumber(run.getNumber());
            context.setStatus(run.getResult() != null ? run.getResult().toString() : "IN_PROGRESS");
            context.setDurationMs(run.getDuration());
            
            if (step.includeLogs) {
                // In real implementation, would get actual logs
                context.setLog("Build log content...");
            }
            
            NexusAIClient.AnalysisResult result = client.analyzeBuild(context);
            
            logger.println("[NexusAI] Analysis complete:");
            logger.println("  Summary: " + result.getSummary());
            if (result.getRootCause() != null) {
                logger.println("  Root Cause: " + result.getRootCause());
            }
            if (result.getSuggestions() != null && !result.getSuggestions().isEmpty()) {
                logger.println("  Suggestions:");
                for (String suggestion : result.getSuggestions()) {
                    logger.println("    - " + suggestion);
                }
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
            return "nexusaiAnalyze";
        }

        @Override
        @Nonnull
        public String getDisplayName() {
            return "Analyze build with NexusAI";
        }
    }
}
