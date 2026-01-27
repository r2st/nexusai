package com.nexusai.plugin.settings

import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.components.PersistentStateComponent
import com.intellij.openapi.components.State
import com.intellij.openapi.components.Storage
import com.intellij.util.xmlb.XmlSerializerUtil

/**
 * Persistent settings for NexusAI plugin.
 */
@State(
    name = "NexusAISettings",
    storages = [Storage("NexusAI.xml")]
)
class NexusAISettings : PersistentStateComponent<NexusAISettings> {
    
    // Connection settings
    var apiEndpoint: String = "https://api.nexusai.dev"
    var apiToken: String = ""
    
    // Feature toggles
    var enableCodeCompletion: Boolean = true
    var enableInlineHints: Boolean = true
    var enableAutoReview: Boolean = false
    var enableTelemetry: Boolean = true
    
    // Model preferences
    var preferredModel: String = "auto"
    var maxTokens: Int = 4096
    var temperature: Double = 0.7
    
    // UI settings
    var showToolWindow: Boolean = true
    var chatPosition: String = "right"
    var darkMode: Boolean = true
    
    // Team settings
    var teamId: String = ""
    var workspaceId: String = ""
    
    // Cache settings
    var enableCache: Boolean = true
    var cacheExpirationMinutes: Int = 60
    
    companion object {
        fun getInstance(): NexusAISettings {
            return ApplicationManager.getApplication()
                .getService(NexusAISettings::class.java)
        }
    }
    
    override fun getState(): NexusAISettings = this
    
    override fun loadState(state: NexusAISettings) {
        XmlSerializerUtil.copyBean(state, this)
    }
    
    fun isConfigured(): Boolean {
        return apiEndpoint.isNotBlank() && apiToken.isNotBlank()
    }
}
