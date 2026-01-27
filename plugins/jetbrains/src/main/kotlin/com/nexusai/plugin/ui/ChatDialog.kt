package com.nexusai.plugin.ui

import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.DialogWrapper
import com.intellij.ui.components.JBScrollPane
import com.intellij.ui.components.JBTextArea
import com.intellij.ui.components.JBTextField
import com.nexusai.plugin.services.CodeContext
import com.nexusai.plugin.services.NexusAIService
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import java.awt.BorderLayout
import java.awt.Dimension
import java.awt.event.KeyAdapter
import java.awt.event.KeyEvent
import javax.swing.*

/**
 * Chat dialog for NexusAI interaction.
 */
class ChatDialog(
    private val project: Project,
    private val initialCode: String? = null,
    private val context: CodeContext? = null
) : DialogWrapper(project, true) {
    
    private val chatHistory = JBTextArea().apply {
        isEditable = false
        lineWrap = true
        wrapStyleWord = true
    }
    
    private val inputField = JBTextField().apply {
        addKeyListener(object : KeyAdapter() {
            override fun keyPressed(e: KeyEvent) {
                if (e.keyCode == KeyEvent.VK_ENTER && !e.isShiftDown) {
                    e.consume()
                    sendMessage()
                }
            }
        })
    }
    
    private val sendButton = JButton("Send").apply {
        addActionListener { sendMessage() }
    }
    
    private var conversationId: String? = null
    
    init {
        title = "NexusAI Chat"
        init()
        
        // If there's initial code, add it to context
        initialCode?.let {
            appendMessage("System", "Code context provided:\n```\n${it.take(500)}${if (it.length > 500) "..." else ""}\n```")
        }
    }
    
    override fun createCenterPanel(): JComponent {
        val panel = JPanel(BorderLayout(10, 10))
        panel.preferredSize = Dimension(600, 500)
        
        // Chat history
        val scrollPane = JBScrollPane(chatHistory)
        scrollPane.preferredSize = Dimension(580, 400)
        panel.add(scrollPane, BorderLayout.CENTER)
        
        // Input area
        val inputPanel = JPanel(BorderLayout(5, 0))
        inputField.preferredSize = Dimension(500, 30)
        inputPanel.add(inputField, BorderLayout.CENTER)
        inputPanel.add(sendButton, BorderLayout.EAST)
        panel.add(inputPanel, BorderLayout.SOUTH)
        
        return panel
    }
    
    private fun sendMessage() {
        val message = inputField.text.trim()
        if (message.isEmpty()) return
        
        inputField.text = ""
        appendMessage("You", message)
        
        // Disable input while processing
        inputField.isEnabled = false
        sendButton.isEnabled = false
        
        CoroutineScope(Dispatchers.Main).launch {
            try {
                val response = NexusAIService.getInstance().chat(
                    message = message,
                    context = context,
                    conversationId = conversationId
                )
                
                conversationId = response.conversationId
                appendMessage("NexusAI", response.message)
                
                response.suggestions?.let { suggestions ->
                    if (suggestions.isNotEmpty()) {
                        appendMessage("", "Suggestions: ${suggestions.joinToString(", ")}")
                    }
                }
            } catch (e: Exception) {
                appendMessage("Error", e.message ?: "Unknown error occurred")
            } finally {
                inputField.isEnabled = true
                sendButton.isEnabled = true
                inputField.requestFocus()
            }
        }
    }
    
    private fun appendMessage(sender: String, message: String) {
        SwingUtilities.invokeLater {
            if (chatHistory.text.isNotEmpty()) {
                chatHistory.append("\n\n")
            }
            if (sender.isNotEmpty()) {
                chatHistory.append("$sender:\n")
            }
            chatHistory.append(message)
            chatHistory.caretPosition = chatHistory.document.length
        }
    }
    
    override fun createActions(): Array<Action> {
        return arrayOf(cancelAction)
    }
}
