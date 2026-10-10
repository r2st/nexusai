---
sidebar_position: 3
---

# Documents

Document intelligence covers **upload → extraction → indexing → retrieval**.

## Pipeline

1. Upload a file
2. Extract text/metadata (PDF/DOCX/XLSX/etc.)
3. Store records in Postgres
4. Index searchable fields (Meilisearch) and optionally embeddings (pgvector)
5. Use retrieval to augment chat responses (RAG)

## Key backend routes

- `POST /documents/upload`
- `GET /documents`
- `GET /documents/{document_id}`
- `POST /documents/search`
- `POST /documents/{document_id}/process`

