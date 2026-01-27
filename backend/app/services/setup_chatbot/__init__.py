"""Setup Chatbot Service.

AI-powered conversational assistant for admin setup operations:
- Connection creation and configuration
- Pipeline/blueprint setup
- Data collection management
- DORA metrics configuration
- Onboarding workflows

Security features:
- Rate limiting
- Input sanitization
- Audit logging
- Credential encryption

UX features:
- Typing indicators
- Error recovery
- Contextual help
- Smart suggestions
- Conversation analytics
"""

from app.services.setup_chatbot.service import (
    SetupChatbotService,
    setup_chatbot_service,
)
from app.services.setup_chatbot.flows import (
    SetupFlow,
    FlowStep,
    FlowState,
    ConnectionSetupFlow,
    ProjectSetupFlow,
    PipelineSetupFlow,
    OnboardingFlow,
)
from app.services.setup_chatbot.schemas import (
    ChatMessage,
    ChatResponse,
    SetupSession,
    PluginConfig,
    ConnectionConfig,
    SetupAction,
    ActionType,
    PLUGIN_CONFIGS,
    PluginType,
    PluginCategory,
    AuthType,
)
from app.services.setup_chatbot.session_store import (
    SessionStore,
    InMemorySessionStore,
    RedisSessionStore,
    get_session_store,
)
from app.services.setup_chatbot.intent_classifier import (
    Intent,
    IntentMatch,
    IntentClassifier,
    classify_intent,
    get_plugin_from_text,
)
from app.services.setup_chatbot.security import (
    RateLimiter,
    RateLimitRule,
    RateLimitResult,
    RateLimitExceeded,
    InputSanitizer,
    AuditLogger,
    AuditEventType,
    AuditEvent,
    CSRFProtection,
    SecurityContext,
    rate_limiter,
    input_sanitizer,
    audit_logger,
    csrf_protection,
    rate_limit,
    audit_action,
    sanitize_input,
)
from app.services.setup_chatbot.encryption import (
    KeyManager,
    EncryptionKey,
    Encryptor,
    FernetEncryptor,
    FallbackEncryptor,
    SecureCredentialStore,
    StoredCredential,
    ConnectionCredentialManager,
    get_encryptor,
    key_manager,
    credential_store,
    connection_credential_manager,
    mask_credential,
)
from app.services.setup_chatbot.ux_helpers import (
    TypingState,
    TypingIndicator,
    TypingIndicatorManager,
    ErrorType,
    ErrorRecoveryInfo,
    RecoveryAction,
    ErrorRecoveryHelper,
    HelpTopic,
    ContextualHelpSystem,
    ProgressInfo,
    typing_indicator_manager,
    error_recovery_helper,
    contextual_help,
    calculate_progress,
)
from app.services.setup_chatbot.validators import (
    ValidationResult,
    ValidationIssue,
    ValidationSeverity,
    FieldValidator,
    RequiredValidator,
    LengthValidator,
    PatternValidator,
    UrlValidator,
    TokenValidator,
    EmailValidator,
    NameValidator,
    CronValidator,
    CompositeValidator,
    SmartSuggestionEngine,
    suggestion_engine,
    create_connection_validator,
    create_project_name_validator,
)
from app.services.setup_chatbot.analytics import (
    FeedbackType,
    FeedbackSentiment,
    ConversationFeedback,
    FeedbackCollector,
    ConversationMetrics,
    ConversationAnalytics,
    PerformanceMetrics,
    PerformanceMonitor,
    UsageAnalytics,
    feedback_collector,
    conversation_analytics,
    performance_monitor,
    usage_analytics,
    get_analytics_dashboard,
)

__all__ = [
    # Service
    "SetupChatbotService",
    "setup_chatbot_service",
    # Flows
    "SetupFlow",
    "FlowStep",
    "FlowState",
    "ConnectionSetupFlow",
    "ProjectSetupFlow",
    "PipelineSetupFlow",
    "OnboardingFlow",
    # Schemas
    "ChatMessage",
    "ChatResponse",
    "SetupSession",
    "PluginConfig",
    "ConnectionConfig",
    "SetupAction",
    "ActionType",
    "PLUGIN_CONFIGS",
    "PluginType",
    "PluginCategory",
    "AuthType",
    # Session Store
    "SessionStore",
    "InMemorySessionStore",
    "RedisSessionStore",
    "get_session_store",
    # Intent Classifier
    "Intent",
    "IntentMatch",
    "IntentClassifier",
    "classify_intent",
    "get_plugin_from_text",
    # Security
    "RateLimiter",
    "RateLimitRule",
    "RateLimitResult",
    "RateLimitExceeded",
    "InputSanitizer",
    "AuditLogger",
    "AuditEventType",
    "AuditEvent",
    "CSRFProtection",
    "SecurityContext",
    "rate_limiter",
    "input_sanitizer",
    "audit_logger",
    "csrf_protection",
    "rate_limit",
    "audit_action",
    "sanitize_input",
    # Encryption
    "KeyManager",
    "EncryptionKey",
    "Encryptor",
    "FernetEncryptor",
    "FallbackEncryptor",
    "SecureCredentialStore",
    "StoredCredential",
    "ConnectionCredentialManager",
    "get_encryptor",
    "key_manager",
    "credential_store",
    "connection_credential_manager",
    "mask_credential",
    # UX Helpers
    "TypingState",
    "TypingIndicator",
    "TypingIndicatorManager",
    "ErrorType",
    "ErrorRecoveryInfo",
    "RecoveryAction",
    "ErrorRecoveryHelper",
    "HelpTopic",
    "ContextualHelpSystem",
    "ProgressInfo",
    "typing_indicator_manager",
    "error_recovery_helper",
    "contextual_help",
    "calculate_progress",
    # Validators
    "ValidationResult",
    "ValidationIssue",
    "ValidationSeverity",
    "FieldValidator",
    "RequiredValidator",
    "LengthValidator",
    "PatternValidator",
    "UrlValidator",
    "TokenValidator",
    "EmailValidator",
    "NameValidator",
    "CronValidator",
    "CompositeValidator",
    "SmartSuggestionEngine",
    "suggestion_engine",
    "create_connection_validator",
    "create_project_name_validator",
    # Analytics
    "FeedbackType",
    "FeedbackSentiment",
    "ConversationFeedback",
    "FeedbackCollector",
    "ConversationMetrics",
    "ConversationAnalytics",
    "PerformanceMetrics",
    "PerformanceMonitor",
    "UsageAnalytics",
    "feedback_collector",
    "conversation_analytics",
    "performance_monitor",
    "usage_analytics",
    "get_analytics_dashboard",
]
