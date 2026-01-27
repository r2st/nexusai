package com.nexusai.plugin.settings

import com.intellij.openapi.options.Configurable
import com.intellij.openapi.ui.DialogPanel
import com.intellij.ui.components.JBCheckBox
import com.intellij.ui.components.JBPasswordField
import com.intellij.ui.components.JBTextField
import com.intellij.ui.dsl.builder.*
import javax.swing.JComponent

/**
 * Settings UI for NexusAI plugin configuration.
 */
class NexusAIConfigurable : Configurable {
    
    private var panel: DialogPanel? = null
    private val settings = NexusAISettings.getInstance()
    
    // Form fields
    private val apiEndpointField = JBTextField()
    private val apiTokenField = JBPasswordField()
    private val enableCompletionCheck = JBCheckBox("Enable code completion")
    private val enableHintsCheck = JBCheckBox("Enable inline hints")
    private val enableAutoReviewCheck = JBCheckBox("Enable auto-review on commit")
    private val enableTelemetryCheck = JBCheckBox("Send anonymous usage data")
    private val teamIdField = JBTextField()
    private val workspaceIdField = JBTextField()
    
    override fun getDisplayName(): String = "NexusAI"
    
    override fun createComponent(): JComponent {
        panel = panel {
            group("Connection") {
                row("API Endpoint:") {
                    cell(apiEndpointField)
                        .columns(COLUMNS_LARGE)
                        .comment("NexusAI API server URL")
                }
                row("API Token:") {
                    cell(apiTokenField)
                        .columns(COLUMNS_LARGE)
                        .comment("Your personal access token")
                }
                row {
                    button("Test Connection") { testConnection() }
                }
            }
            
            group("Features") {
                row {
                    cell(enableCompletionCheck)
                }
                row {
                    cell(enableHintsCheck)
                }
                row {
                    cell(enableAutoReviewCheck)
                }
            }
            
            group("Team (Optional)") {
                row("Team ID:") {
                    cell(teamIdField)
                        .columns(COLUMNS_MEDIUM)
                }
                row("Workspace ID:") {
                    cell(workspaceIdField)
                        .columns(COLUMNS_MEDIUM)
                }
            }
            
            group("Privacy") {
                row {
                    cell(enableTelemetryCheck)
                        .comment("Help improve NexusAI by sending anonymous usage statistics")
                }
            }
        }
        
        reset()
        return panel!!
    }
    
    override fun isModified(): Boolean {
        return apiEndpointField.text != settings.apiEndpoint ||
                String(apiTokenField.password) != settings.apiToken ||
                enableCompletionCheck.isSelected != settings.enableCodeCompletion ||
                enableHintsCheck.isSelected != settings.enableInlineHints ||
                enableAutoReviewCheck.isSelected != settings.enableAutoReview ||
                enableTelemetryCheck.isSelected != settings.enableTelemetry ||
                teamIdField.text != settings.teamId ||
                workspaceIdField.text != settings.workspaceId
    }
    
    override fun apply() {
        settings.apiEndpoint = apiEndpointField.text
        settings.apiToken = String(apiTokenField.password)
        settings.enableCodeCompletion = enableCompletionCheck.isSelected
        settings.enableInlineHints = enableHintsCheck.isSelected
        settings.enableAutoReview = enableAutoReviewCheck.isSelected
        settings.enableTelemetry = enableTelemetryCheck.isSelected
        settings.teamId = teamIdField.text
        settings.workspaceId = workspaceIdField.text
    }
    
    override fun reset() {
        apiEndpointField.text = settings.apiEndpoint
        apiTokenField.text = settings.apiToken
        enableCompletionCheck.isSelected = settings.enableCodeCompletion
        enableHintsCheck.isSelected = settings.enableInlineHints
        enableAutoReviewCheck.isSelected = settings.enableAutoReview
        enableTelemetryCheck.isSelected = settings.enableTelemetry
        teamIdField.text = settings.teamId
        workspaceIdField.text = settings.workspaceId
    }
    
    private fun testConnection() {
        // TODO: Implement connection test
        com.intellij.openapi.ui.Messages.showInfoMessage(
            "Connection test not implemented yet",
            "NexusAI"
        )
    }
}
