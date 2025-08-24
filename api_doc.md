# API Documentation

## Overview

This API provides comprehensive file management, user authentication, and data processing capabilities. All endpoints return JSON responses and require proper authentication headers.

## Authentication

### Headers Required
All API requests must include the following headers:
- `Authorization: Bearer <your-token>`
- `Content-Type: application/json`

## Base URL
```
https://api.example.com/v1
```

## Endpoints

### User Management

#### Create User
**POST** `/users`

Creates a new user account with the provided information.

**Request Body:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `email` | string | Yes | - | User's email address |
| `password` | string | Yes | - | Password (min 8 characters) |
| `first_name` | string | Yes | - | User's first name |
| `last_name` | string | No | - | User's last name |
| `phone` | string | No | - | Phone number (optional) |

**Response:**
```json
{
  "id": "user_123",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### Get User Profile
**GET** `/users/{user_id}`

Retrieves user profile information.

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `user_id` | string | Yes | Unique user identifier |

**Response:**
```json
{
  "id": "user_123",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+1234567890",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-20T14:22:00Z"
}
```

### File Management

#### Upload File
**POST** `/files/upload`

Uploads a file to the system. Supports multiple file formats and automatic processing.

**Request Body:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `file` | file | Yes | - | File to upload (max 100MB) |
| `folder_id` | string | No | root | Target folder ID |
| `description` | string | No | - | Optional file description |
| `tags` | array | No | [] | Array of tag strings |
| `public` | boolean | No | false | Make file publicly accessible |

**Supported File Types:**
- Images: JPG, PNG, GIF, WebP (max 10MB)
- Documents: PDF, DOC, DOCX, TXT (max 50MB)
- Videos: MP4, AVI, MOV (max 100MB)
- Archives: ZIP, RAR (max 25MB)

**Response:**
```json
{
  "id": "file_456",
  "name": "document.pdf",
  "size": 2048576,
  "type": "application/pdf",
  "url": "https://cdn.example.com/files/file_456",
  "folder_id": "folder_123",
  "uploaded_at": "2024-01-15T11:45:00Z",
  "processing_status": "completed"
}
```

#### List Files
**GET** `/files`

Retrieves a paginated list of files with optional filtering.

**Query Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `page` | integer | No | 1 | Page number (1-based) |
| `limit` | integer | No | 20 | Items per page (max 100) |
| `folder_id` | string | No | - | Filter by folder ID |
| `type` | string | No | - | Filter by file type |
| `search` | string | No | - | Search in filename and description |
| `sort_by` | string | No | uploaded_at | Sort field (name, size, uploaded_at) |
| `sort_order` | string | No | desc | Sort order (asc, desc) |

**Response:**
```json
{
  "files": [
    {
      "id": "file_456",
      "name": "document.pdf",
      "size": 2048576,
      "type": "application/pdf",
      "folder_id": "folder_123",
      "uploaded_at": "2024-01-15T11:45:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 150,
    "pages": 8
  }
}
```

#### Download File
**GET** `/files/{file_id}/download`

Downloads a file by its ID.

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `file_id` | string | Yes | Unique file identifier |

**Response:**
Returns the file as a binary stream with appropriate headers.

### Folder Management

#### Create Folder
**POST** `/folders`

Creates a new folder in the file system.

**Request Body:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `name` | string | Yes | - | Folder name |
| `parent_id` | string | No | root | Parent folder ID |
| `description` | string | No | - | Optional folder description |

**Response:**
```json
{
  "id": "folder_789",
  "name": "My Documents",
  "parent_id": "folder_123",
  "path": "/My Documents",
  "created_at": "2024-01-15T12:00:00Z"
}
```

#### List Folders
**GET** `/folders`

Retrieves a hierarchical list of folders.

**Query Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `parent_id` | string | No | root | Show only children of this folder |
| `include_files` | boolean | No | false | Include file count in response |

**Response:**
```json
{
  "folders": [
    {
      "id": "folder_123",
      "name": "Documents",
      "parent_id": "root",
      "path": "/Documents",
      "file_count": 15,
      "created_at": "2024-01-10T09:00:00Z"
    }
  ]
}
```

### Data Processing

#### Process Data
**POST** `/data/process`

Processes data with various algorithms and returns results.

**Request Body:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `data` | array | Yes | - | Array of data points |
| `algorithm` | string | Yes | - | Processing algorithm (sort, filter, analyze) |
| `options` | object | No | {} | Algorithm-specific options |
| `format` | string | No | json | Output format (json, csv, xml) |

**Algorithm Options:**
- `sort`: `field` (string), `order` (asc/desc)
- `filter`: `criteria` (object), `operator` (and/or)
- `analyze`: `metrics` (array), `group_by` (string)

**Response:**
```json
{
  "result": [...],
  "processing_time": 0.245,
  "algorithm": "sort",
  "total_records": 1000
}
```

### Error Handling

#### Error Response Format
All API errors follow this standard format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid email format",
    "details": {
      "field": "email",
      "value": "invalid-email"
    }
  }
}
```

#### Common Error Codes
| Code | HTTP Status | Description |
|------|-------------|-------------|
| `AUTHENTICATION_ERROR` | 401 | Invalid or missing authentication |
| `AUTHORIZATION_ERROR` | 403 | Insufficient permissions |
| `VALIDATION_ERROR` | 400 | Invalid request parameters |
| `NOT_FOUND` | 404 | Resource not found |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |

### Rate Limiting

API requests are rate-limited to ensure fair usage:

- **Standard Plan**: 1000 requests per hour
- **Premium Plan**: 10000 requests per hour
- **Enterprise Plan**: 100000 requests per hour

Rate limit headers are included in all responses:
- `X-RateLimit-Limit`: Maximum requests per hour
- `X-RateLimit-Remaining`: Remaining requests in current hour
- `X-RateLimit-Reset`: Time when rate limit resets (Unix timestamp)

### Webhooks

#### Configure Webhook
**POST** `/webhooks`

Sets up webhook notifications for various events.

**Request Body:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `url` | string | Yes | - | Webhook endpoint URL |
| `events` | array | Yes | - | Array of event types to listen for |
| `secret` | string | No | - | Secret for signature verification |
| `active` | boolean | No | true | Whether webhook is active |

**Supported Events:**
- `file.uploaded`: File upload completed
- `file.deleted`: File deleted
- `user.created`: New user registered
- `folder.created`: New folder created
- `data.processed`: Data processing completed

**Response:**
```json
{
  "id": "webhook_123",
  "url": "https://your-app.com/webhooks",
  "events": ["file.uploaded", "user.created"],
  "active": true,
  "created_at": "2024-01-15T13:00:00Z"
}
```

### SDK Examples

#### JavaScript/Node.js
```javascript
const api = require('@example/api-client');

// Upload a file
const file = await api.files.upload({
  file: fs.createReadStream('document.pdf'),
  folder_id: 'folder_123',
  description: 'Important document'
});

// Process data
const result = await api.data.process({
  data: [1, 2, 3, 4, 5],
  algorithm: 'sort',
  options: { field: 'value', order: 'asc' }
});
```

#### Python
```python
import example_api

client = example_api.Client(api_key='your-key')

# Create user
user = client.users.create(
    email='user@example.com',
    password='secure_password',
    first_name='John',
    last_name='Doe'
)

# List files
files = client.files.list(
    page=1,
    limit=20,
    folder_id='folder_123'
)
```

### Best Practices

1. **Authentication**: Always use HTTPS and secure token storage
2. **Error Handling**: Implement proper error handling for all API calls
3. **Rate Limiting**: Monitor rate limit headers and implement backoff strategies
4. **File Uploads**: Use multipart/form-data for file uploads
5. **Pagination**: Always handle pagination for list endpoints
6. **Webhooks**: Verify webhook signatures for security
7. **Caching**: Cache responses when appropriate to reduce API calls 

http://127.0.0.1:8080/v1/objects?class=RAGDocs