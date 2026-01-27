// =============================================================================
// MongoDB Initialization Script
// =============================================================================

// Switch to the nexusai database
db = db.getSiblingDB('nexusai');

// Create application user with appropriate roles
db.createUser({
  user: 'nexusai_app',
  pwd: process.env.MONGODB_APP_PASSWORD || 'change-me-in-production',
  roles: [
    { role: 'readWrite', db: 'nexusai' },
    { role: 'dbAdmin', db: 'nexusai' }
  ]
});

// Create collections with schema validation
db.createCollection('conversations', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['tenant_id', 'user_id', 'created_at'],
      properties: {
        tenant_id: {
          bsonType: 'string',
          description: 'Tenant identifier for multi-tenancy'
        },
        user_id: {
          bsonType: 'string',
          description: 'User who owns this conversation'
        },
        title: {
          bsonType: 'string',
          description: 'Conversation title'
        },
        messages: {
          bsonType: 'array',
          items: {
            bsonType: 'object',
            required: ['role', 'content', 'timestamp'],
            properties: {
              role: {
                enum: ['user', 'assistant', 'system'],
                description: 'Message role'
              },
              content: {
                bsonType: 'string',
                description: 'Message content'
              },
              timestamp: {
                bsonType: 'date',
                description: 'Message timestamp'
              },
              model: {
                bsonType: 'string',
                description: 'AI model used'
              },
              tokens: {
                bsonType: 'object',
                properties: {
                  input: { bsonType: 'int' },
                  output: { bsonType: 'int' }
                }
              }
            }
          }
        },
        metadata: {
          bsonType: 'object',
          description: 'Additional metadata'
        },
        created_at: {
          bsonType: 'date',
          description: 'Creation timestamp'
        },
        updated_at: {
          bsonType: 'date',
          description: 'Last update timestamp'
        }
      }
    }
  }
});

db.createCollection('documents', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['tenant_id', 'filename', 'created_at'],
      properties: {
        tenant_id: {
          bsonType: 'string',
          description: 'Tenant identifier'
        },
        user_id: {
          bsonType: 'string',
          description: 'User who uploaded the document'
        },
        filename: {
          bsonType: 'string',
          description: 'Original filename'
        },
        content_type: {
          bsonType: 'string',
          description: 'MIME type'
        },
        size_bytes: {
          bsonType: 'long',
          description: 'File size in bytes'
        },
        storage_path: {
          bsonType: 'string',
          description: 'Path in storage backend'
        },
        extracted_text: {
          bsonType: 'string',
          description: 'Extracted text content'
        },
        chunks: {
          bsonType: 'array',
          items: {
            bsonType: 'object',
            properties: {
              text: { bsonType: 'string' },
              embedding: { bsonType: 'array' },
              metadata: { bsonType: 'object' }
            }
          }
        },
        metadata: {
          bsonType: 'object',
          description: 'Document metadata'
        },
        created_at: {
          bsonType: 'date'
        },
        updated_at: {
          bsonType: 'date'
        }
      }
    }
  }
});

db.createCollection('agents', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['name', 'type', 'created_at'],
      properties: {
        tenant_id: {
          bsonType: 'string'
        },
        name: {
          bsonType: 'string'
        },
        description: {
          bsonType: 'string'
        },
        type: {
          enum: ['chat', 'code', 'analysis', 'devops', 'custom']
        },
        model: {
          bsonType: 'string'
        },
        system_prompt: {
          bsonType: 'string'
        },
        tools: {
          bsonType: 'array',
          items: {
            bsonType: 'string'
          }
        },
        parameters: {
          bsonType: 'object'
        },
        is_public: {
          bsonType: 'bool'
        },
        created_at: {
          bsonType: 'date'
        },
        updated_at: {
          bsonType: 'date'
        }
      }
    }
  }
});

// Create indexes for performance
db.conversations.createIndex({ tenant_id: 1, user_id: 1 });
db.conversations.createIndex({ tenant_id: 1, created_at: -1 });
db.conversations.createIndex({ tenant_id: 1, 'messages.content': 'text' });

db.documents.createIndex({ tenant_id: 1, user_id: 1 });
db.documents.createIndex({ tenant_id: 1, created_at: -1 });
db.documents.createIndex({ tenant_id: 1, filename: 'text', extracted_text: 'text' });

db.agents.createIndex({ tenant_id: 1, name: 1 });
db.agents.createIndex({ type: 1, is_public: 1 });

print('MongoDB initialization completed successfully!');
