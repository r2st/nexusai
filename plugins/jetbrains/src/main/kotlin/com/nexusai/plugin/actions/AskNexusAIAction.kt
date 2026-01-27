package com.nexusai.plugin.actions

import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.CommonDataKeys
import com.intellij.openapi.ui.Messages
import com.nexusai.plugin.services.CodeContext
import com.nexusai.plugin.services.NexusAIService
import com.nexusai.plugin.settings.NexusAISettings
import com.nexusai.plugin.ui.ChatDialog
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

/**
 * Action to ask NexusAI about selected code.
 */
class AskNexusAIAction : AnAction() {
    
    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        val editor = e.getData(CommonDataKeys.EDITOR) ?: return
        
        // Check configuration
        if (!NexusAISettings.getInstance().isConfigured()) {
            Messages.showWarningDialog(
                project,
                "Please configure NexusAI in Settings → Tools → NexusAI",
                "NexusAI Not Configured"
            )
            return
        }
        
        // Get selected text or current line
        val selectionModel = editor.selectionModel
        val selectedText = selectionModel.selectedText ?: run {
            val document = editor.document
            val caretOffset = editor.caretModel.offset
            val lineNumber = document.getLineNumber(caretOffset)
            val lineStart = document.getLineStartOffset(lineNumber)
            val lineEnd = document.getLineEndOffset(lineNumber)
            document.getText(com.intellij.openapi.util.TextRange(lineStart, lineEnd))
        }
        
        // Get file context
        val virtualFile = e.getData(CommonDataKeys.VIRTUAL_FILE)
        val context = CodeContext(
            filePath = virtualFile?.path,
            projectName = project.name,
            language = virtualFile?.extension
        )
        
        // Open chat dialog with context
        ChatDialog(project, selectedText, context).show()
    }
    
    override fun update(e: AnActionEvent) {
        val editor = e.getData(CommonDataKeys.EDITOR)
        e.presentation.isEnabledAndVisible = editor != null
    }
}

/**
 * Action to explain selected code.
 */
class ExplainCodeAction : AnAction() {
    
    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        val editor = e.getData(CommonDataKeys.EDITOR) ?: return
        
        if (!NexusAISettings.getInstance().isConfigured()) {
            Messages.showWarningDialog(
                project,
                "Please configure NexusAI in Settings → Tools → NexusAI",
                "NexusAI Not Configured"
            )
            return
        }
        
        val selectedText = editor.selectionModel.selectedText
        if (selectedText.isNullOrBlank()) {
            Messages.showWarningDialog(
                project,
                "Please select some code to explain",
                "No Selection"
            )
            return
        }
        
        val virtualFile = e.getData(CommonDataKeys.VIRTUAL_FILE)
        val language = virtualFile?.extension ?: "text"
        
        CoroutineScope(Dispatchers.Main).launch {
            try {
                val response = NexusAIService.getInstance()
                    .explainCode(selectedText, language)
                
                Messages.showInfoMessage(
                    project,
                    response.explanation,
                    "Code Explanation"
                )
            } catch (ex: Exception) {
                Messages.showErrorDialog(
                    project,
                    "Failed to get explanation: ${ex.message}",
                    "Error"
                )
            }
        }
    }
    
    override fun update(e: AnActionEvent) {
        val editor = e.getData(CommonDataKeys.EDITOR)
        e.presentation.isEnabledAndVisible = 
            editor != null && editor.selectionModel.hasSelection()
    }
}

/**
 * Action to generate documentation.
 */
class GenerateDocsAction : AnAction() {
    
    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        val editor = e.getData(CommonDataKeys.EDITOR) ?: return
        
        if (!NexusAISettings.getInstance().isConfigured()) {
            Messages.showWarningDialog(
                project,
                "Please configure NexusAI in Settings → Tools → NexusAI",
                "NexusAI Not Configured"
            )
            return
        }
        
        val selectedText = editor.selectionModel.selectedText
        if (selectedText.isNullOrBlank()) {
            Messages.showWarningDialog(
                project,
                "Please select code to document",
                "No Selection"
            )
            return
        }
        
        val virtualFile = e.getData(CommonDataKeys.VIRTUAL_FILE)
        val language = virtualFile?.extension ?: "text"
        
        CoroutineScope(Dispatchers.Main).launch {
            try {
                val response = NexusAIService.getInstance()
                    .generateDocs(selectedText, language)
                
                // Insert documentation above selection
                val document = editor.document
                val selectionStart = editor.selectionModel.selectionStart
                val lineNumber = document.getLineNumber(selectionStart)
                val lineStart = document.getLineStartOffset(lineNumber)
                
                com.intellij.openapi.command.WriteCommandAction.runWriteCommandAction(project) {
                    document.insertString(lineStart, response.documentation + "\n")
                }
            } catch (ex: Exception) {
                Messages.showErrorDialog(
                    project,
                    "Failed to generate docs: ${ex.message}",
                    "Error"
                )
            }
        }
    }
    
    override fun update(e: AnActionEvent) {
        val editor = e.getData(CommonDataKeys.EDITOR)
        e.presentation.isEnabledAndVisible = 
            editor != null && editor.selectionModel.hasSelection()
    }
}

/**
 * Action to review selected code.
 */
class ReviewCodeAction : AnAction() {
    
    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        val editor = e.getData(CommonDataKeys.EDITOR) ?: return
        
        if (!NexusAISettings.getInstance().isConfigured()) {
            Messages.showWarningDialog(
                project,
                "Please configure NexusAI in Settings → Tools → NexusAI",
                "NexusAI Not Configured"
            )
            return
        }
        
        val selectedText = editor.selectionModel.selectedText
        if (selectedText.isNullOrBlank()) {
            Messages.showWarningDialog(
                project,
                "Please select code to review",
                "No Selection"
            )
            return
        }
        
        val virtualFile = e.getData(CommonDataKeys.VIRTUAL_FILE)
        val language = virtualFile?.extension ?: "text"
        
        CoroutineScope(Dispatchers.Main).launch {
            try {
                val response = NexusAIService.getInstance()
                    .reviewCode(selectedText, language)
                
                val issuesText = if (response.issues.isEmpty()) {
                    "No issues found!"
                } else {
                    response.issues.joinToString("\n\n") { issue ->
                        "[${issue.severity}] ${issue.message}" +
                            (issue.line?.let { "\nLine: $it" } ?: "") +
                            (issue.suggestion?.let { "\nSuggestion: $it" } ?: "")
                    }
                }
                
                Messages.showInfoMessage(
                    project,
                    "${response.summary}\n\n$issuesText",
                    "Code Review"
                )
            } catch (ex: Exception) {
                Messages.showErrorDialog(
                    project,
                    "Failed to review code: ${ex.message}",
                    "Error"
                )
            }
        }
    }
    
    override fun update(e: AnActionEvent) {
        val editor = e.getData(CommonDataKeys.EDITOR)
        e.presentation.isEnabledAndVisible = 
            editor != null && editor.selectionModel.hasSelection()
    }
}

/**
 * Action to get refactoring suggestions.
 */
class RefactorSuggestionsAction : AnAction() {
    
    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        val editor = e.getData(CommonDataKeys.EDITOR) ?: return
        
        if (!NexusAISettings.getInstance().isConfigured()) {
            Messages.showWarningDialog(
                project,
                "Please configure NexusAI in Settings → Tools → NexusAI",
                "NexusAI Not Configured"
            )
            return
        }
        
        val selectedText = editor.selectionModel.selectedText
        if (selectedText.isNullOrBlank()) {
            Messages.showWarningDialog(
                project,
                "Please select code to analyze",
                "No Selection"
            )
            return
        }
        
        val virtualFile = e.getData(CommonDataKeys.VIRTUAL_FILE)
        val language = virtualFile?.extension ?: "text"
        
        CoroutineScope(Dispatchers.Main).launch {
            try {
                val response = NexusAIService.getInstance()
                    .suggestRefactoring(selectedText, language)
                
                if (response.suggestions.isEmpty()) {
                    Messages.showInfoMessage(
                        project,
                        "No refactoring suggestions for this code.",
                        "Refactoring"
                    )
                } else {
                    val text = response.suggestions.joinToString("\n\n---\n\n") { suggestion ->
                        "**${suggestion.title}**\n${suggestion.description}"
                    }
                    Messages.showInfoMessage(project, text, "Refactoring Suggestions")
                }
            } catch (ex: Exception) {
                Messages.showErrorDialog(
                    project,
                    "Failed to get suggestions: ${ex.message}",
                    "Error"
                )
            }
        }
    }
    
    override fun update(e: AnActionEvent) {
        val editor = e.getData(CommonDataKeys.EDITOR)
        e.presentation.isEnabledAndVisible = 
            editor != null && editor.selectionModel.hasSelection()
    }
}

/**
 * Action to open the chat window.
 */
class OpenChatAction : AnAction() {
    
    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        
        if (!NexusAISettings.getInstance().isConfigured()) {
            Messages.showWarningDialog(
                project,
                "Please configure NexusAI in Settings → Tools → NexusAI",
                "NexusAI Not Configured"
            )
            return
        }
        
        ChatDialog(project).show()
    }
}
