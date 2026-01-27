# Signed URL Implementation Plan

## Overview

This document describes the implementation of signed URL workflows for secure file transfer in NexusAI, enabling secure uploads and downloads without exposing storage credentials.

## Architecture

### 1. Signed URL Service

**Location**: `backend/app/api/signed_urls.py`

Provides:
- Pre-signed upload URLs
- Pre-signed download URLs
- URL expiration management
- Access control integration

### 2. Storage Backend Support

All storage backends support signed URLs:
- **S3**: Pre-signed URLs via boto3
- **GCS**: Signed URLs via Google Cloud Storage
- **Azure**: SAS URLs via Azure Blob Storage
- **Local**: Token-based URLs (development)

### 3. Workflow

```
User Request
    ↓
Generate Signed URL (with expiration)
    ↓
Return URL to User
    ↓
User Uses URL (upload/download)
    ↓
Storage Validates Signature
    ↓
Operation Completes
```

## Implementation

### API Endpoints

#### Generate Signed URL

```http
POST /api/v1/signed-urls/generate
Content-Type: application/json

{
  "file_key": "documents/user123/file.pdf",
  "operation": "download",
  "expires_in": 3600
}
```

Response:
```json
{
  "url": "https://storage.example.com/file.pdf?signature=...",
  "expires_at": "2024-01-01T01:00:00Z",
  "file_key": "documents/user123/file.pdf",
  "operation": "download",
  "method": "GET"
}
```

#### Generate Upload URL

```http
POST /api/v1/signed-urls/upload
?filename=document.pdf
&category=document
&expires_in=3600
&content_type=application/pdf
```

Response:
```json
{
  "url": "https://storage.example.com/upload?signature=...",
  "expires_at": "2024-01-01T01:00:00Z",
  "file_key": "documents/user123/document.pdf",
  "operation": "upload",
  "method": "POST",
  "fields": {
    "key": "documents/user123/document.pdf",
    "Content-Type": "application/pdf"
  }
}
```

#### Generate Download URL

```http
GET /api/v1/signed-urls/download/{file_key}?expires_in=3600
```

## Security

### 1. Access Control

- All signed URLs require authentication
- User must have access to the file
- URLs are scoped to user's permissions

### 2. Expiration

- URLs expire after specified time (default: 1 hour)
- Maximum expiration: 24 hours
- Minimum expiration: 1 minute

### 3. Validation

- Signature validation at storage level
- User permission validation at API level
- File existence validation

## Usage Examples

### Upload Workflow

```python
# 1. Request upload URL
response = await client.post(
    "/api/v1/signed-urls/upload",
    params={
        "filename": "report.pdf",
        "category": "document",
        "expires_in": 3600,
        "content_type": "application/pdf"
    }
)

# 2. Upload file using signed URL
upload_response = await requests.post(
    response.json()["url"],
    files={"file": open("report.pdf", "rb")},
    data=response.json()["fields"]
)
```

### Download Workflow

```python
# 1. Request download URL
response = await client.get(
    f"/api/v1/signed-urls/download/{file_key}",
    params={"expires_in": 3600}
)

# 2. Download file using signed URL
file_data = await requests.get(response.json()["url"])
```

## Integration Points

### 1. Document Service

Documents use signed URLs for:
- Secure file access
- Temporary download links
- Upload workflows

### 2. Code Interpreter

Code interpreter uses signed URLs for:
- File uploads
- Result downloads
- Temporary file access

### 3. Image Generation

Image generation uses signed URLs for:
- Generated image downloads
- Upload of reference images

## Configuration

Set in environment variables:
- `S3_URL_EXPIRY_SECONDS`: Default S3 URL expiration (default: 3600)
- `GCS_URL_EXPIRY_SECONDS`: Default GCS URL expiration (default: 3600)
- `AZURE_URL_EXPIRY_SECONDS`: Default Azure URL expiration (default: 3600)

## Best Practices

1. **Short Expiration**: Use shortest practical expiration time
2. **HTTPS Only**: Always use HTTPS for signed URLs
3. **Access Validation**: Validate user access before generating URL
4. **Audit Logging**: Log all signed URL generation
5. **Token Rotation**: Rotate signing keys regularly

## Monitoring

Monitor signed URL usage:
- Generation rate
- Usage rate
- Expiration rate
- Access denials

## References

- Signed URL API: `backend/app/api/signed_urls.py`
- Storage Backends: `backend/app/services/storage/`
- S3 Implementation: `backend/app/services/storage/s3.py`
- GCS Implementation: `backend/app/services/storage/gcs.py`
