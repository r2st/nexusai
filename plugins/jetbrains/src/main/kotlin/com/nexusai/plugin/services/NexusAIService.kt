package com.nexusai.plugin.services

import com.google.gson.Gson
import com.google.gson.JsonObject
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.components.Service
import com.nexusai.plugin.settings.NexusAISettings
import kotlinx.coroutines.*
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.IOException
import java.util.concurrent.TimeUnit

/**
 * Core service for NexusAI API communication.
 */
@Service(Service.Level.APP)
class NexusAIService {
    
    private val gson = Gson()
    private val settings = NexusAISettings.getInstance()
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    
    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(120, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .build()
    
    companion object {
        fun getInstance(): NexusAIService {
            return ApplicationManager.getApplication()
                .getService(NexusAIService::class.java)
        }
    }
    
    /**
     * Send a chat message to NexusAI.
     */
    suspend fun chat(
        message: String,
        context: CodeContext? = null,
        conversationId: String? = null
    ): ChatResponse {
        val payload = JsonObject().apply {
            addProperty("message", message)
            conversationId?.let { addProperty("conversation_id", it) }
            context?.let { ctx ->
                add("context", gson.toJsonTree(ctx))
            }
        }
        
        val response = makeRequest("/api/v2/chat", payload)
        return gson.fromJson(response, ChatResponse::class.java)
    }
    
    /**
     * Get code explanation.
     */
    suspend fun explainCode(code: String, language: String): ExplanationResponse {
        val payload = JsonObject().apply {
            addProperty("code", code)
            addProperty("language", language)
        }
        
        val response = makeRequest("/api/v2/explain", payload)
        return gson.fromJson(response, ExplanationResponse::class.java)
    }
    
    /**
     * Generate documentation for code.
     */
    suspend fun generateDocs(
        code: String,
        language: String,
        style: String = "jsdoc"
    ): DocsResponse {
        val payload = JsonObject().apply {
            addProperty("code", code)
            addProperty("language", language)
            addProperty("style", style)
        }
        
        val response = makeRequest("/api/v2/docs/generate", payload)
        return gson.fromJson(response, DocsResponse::class.java)
    }
    
    /**
     * Review code for issues.
     */
    suspend fun reviewCode(
        code: String,
        language: String,
        context: CodeContext? = null
    ): ReviewResponse {
        val payload = JsonObject().apply {
            addProperty("code", code)
            addProperty("language", language)
            context?.let { add("context", gson.toJsonTree(it)) }
        }
        
        val response = makeRequest("/api/v2/review", payload)
        return gson.fromJson(response, ReviewResponse::class.java)
    }
    
    /**
     * Get refactoring suggestions.
     */
    suspend fun suggestRefactoring(
        code: String,
        language: String
    ): RefactoringResponse {
        val payload = JsonObject().apply {
            addProperty("code", code)
            addProperty("language", language)
        }
        
        val response = makeRequest("/api/v2/refactor/suggest", payload)
        return gson.fromJson(response, RefactoringResponse::class.java)
    }
    
    /**
     * Get code completions.
     */
    suspend fun getCompletions(
        prefix: String,
        suffix: String,
        language: String,
        maxResults: Int = 3
    ): CompletionResponse {
        val payload = JsonObject().apply {
            addProperty("prefix", prefix)
            addProperty("suffix", suffix)
            addProperty("language", language)
            addProperty("max_results", maxResults)
        }
        
        val response = makeRequest("/api/v2/complete", payload)
        return gson.fromJson(response, CompletionResponse::class.java)
    }
    
    /**
     * Review a pull request.
     */
    suspend fun reviewPullRequest(
        repo: String,
        prNumber: Int,
        diff: String
    ): PRReviewResponse {
        val payload = JsonObject().apply {
            addProperty("repo", repo)
            addProperty("pr_number", prNumber)
            addProperty("diff", diff)
        }
        
        val response = makeRequest("/api/v2/pr/review", payload)
        return gson.fromJson(response, PRReviewResponse::class.java)
    }
    
    /**
     * Test API connection.
     */
    suspend fun testConnection(): Boolean {
        return try {
            val response = makeRequest("/api/v2/health", JsonObject())
            response.has("status")
        } catch (e: Exception) {
            false
        }
    }
    
    private suspend fun makeRequest(endpoint: String, payload: JsonObject): JsonObject {
        return withContext(Dispatchers.IO) {
            val url = "${settings.apiEndpoint}$endpoint"
            val json = gson.toJson(payload)
            
            val request = Request.Builder()
                .url(url)
                .addHeader("Authorization", "Bearer ${settings.apiToken}")
                .addHeader("Content-Type", "application/json")
                .addHeader("X-Client", "jetbrains-plugin")
                .post(json.toRequestBody("application/json".toMediaType()))
                .build()
            
            val response = client.newCall(request).execute()
            
            if (!response.isSuccessful) {
                throw IOException("API request failed: ${response.code}")
            }
            
            val body = response.body?.string() ?: "{}"
            gson.fromJson(body, JsonObject::class.java)
        }
    }
    
    fun dispose() {
        scope.cancel()
    }
}

// Data classes for API responses

data class CodeContext(
    val filePath: String? = null,
    val projectName: String? = null,
    val language: String? = null,
    val imports: List<String>? = null,
    val relatedFiles: List<String>? = null
)

data class ChatResponse(
    val message: String,
    val conversationId: String?,
    val suggestions: List<String>?
)

data class ExplanationResponse(
    val explanation: String,
    val summary: String?,
    val concepts: List<String>?
)

data class DocsResponse(
    val documentation: String,
    val format: String
)

data class ReviewResponse(
    val issues: List<CodeIssue>,
    val summary: String,
    val score: Int?
)

data class CodeIssue(
    val type: String,
    val severity: String,
    val message: String,
    val line: Int?,
    val suggestion: String?
)

data class RefactoringResponse(
    val suggestions: List<RefactoringSuggestion>
)

data class RefactoringSuggestion(
    val title: String,
    val description: String,
    val before: String,
    val after: String,
    val impact: String?
)

data class CompletionResponse(
    val completions: List<CodeCompletion>
)

data class CodeCompletion(
    val text: String,
    val displayText: String?,
    val detail: String?
)

data class PRReviewResponse(
    val summary: String,
    val riskLevel: String,
    val comments: List<PRComment>,
    val approvalRecommendation: String
)

data class PRComment(
    val path: String,
    val line: Int,
    val body: String,
    val severity: String
)
