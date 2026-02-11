# Hetzner Agent Upload Endpoint Spec

## Endpoint to Add

**POST** `http://46.225.82.130:9090/agent/upload`

### Headers
```
Authorization: Bearer dytto-agent-token-v1
Content-Type: multipart/form-data
```

### Body (multipart/form-data)
```
file: <binary file data>
user_id: <org_id>  // e.g., "ff-perscholas" or just the org UUID
agent_type: "fundfish"  // optional, defaults to fundfish
```

### Response (200 OK)
```json
{
  "status": "success",
  "file": {
    "filename": "document.pdf",
    "path": "/home/dytto-agent/workspaces/ff-{org_id}/uploads/document.pdf",
    "size": 1234567,
    "uploaded_at": "2026-02-11T00:15:00Z"
  }
}
```

### Error Responses
```json
// 400 - Bad Request
{
  "status": "error",
  "error": "No file provided" | "File too large" | "Invalid file type"
}

// 401 - Unauthorized
{
  "status": "error",
  "error": "Invalid token"
}

// 500 - Server Error
{
  "status": "error",
  "error": "Failed to save file: <reason>"
}
```

## Implementation Notes

1. **File Validation:**
   - Max size: 10MB
   - Allowed types: PDF, DOCX, TXT, MD
   - Reject anything else

2. **File Storage:**
   - Save to: `/home/dytto-agent/workspaces/ff-{org_id}/uploads/{filename}`
   - Create directories if they don't exist
   - Sanitize filename (alphanumeric + dots, dashes, underscores only)

3. **Agent Awareness:**
   - Update agent's TOOLS.md to mention uploads directory
   - Or add to workspace README/context

4. **Security:**
   - Verify token matches `AGENT_BRIDGE_TOKEN`
   - No path traversal (sanitize filenames)
   - Delete files older than 30 days (optional cleanup cron)

## Example Node.js Implementation

```javascript
const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs-extra');

const upload = multer({
  limits: { fileSize: 10 * 1024 * 1024 }, // 10MB
  fileFilter: (req, file, cb) => {
    const allowed = ['.pdf', '.docx', '.txt', '.md'];
    const ext = path.extname(file.originalname).toLowerCase();
    if (allowed.includes(ext)) {
      cb(null, true);
    } else {
      cb(new Error('Invalid file type'));
    }
  }
});

router.post('/agent/upload', 
  verifyToken,
  upload.single('file'),
  async (req, res) => {
    try {
      const { user_id, agent_type = 'fundfish' } = req.body;
      
      if (!req.file) {
        return res.status(400).json({ status: 'error', error: 'No file provided' });
      }
      
      // Sanitize filename
      const sanitized = req.file.originalname.replace(/[^a-zA-Z0-9.-_]/g, '_');
      
      // Workspace path
      const workspacePath = `/home/dytto-agent/workspaces/ff-${user_id}/uploads`;
      await fs.ensureDir(workspacePath);
      
      // Save file
      const filePath = path.join(workspacePath, sanitized);
      await fs.writeFile(filePath, req.file.buffer);
      
      res.json({
        status: 'success',
        file: {
          filename: sanitized,
          path: filePath,
          size: req.file.size,
          uploaded_at: new Date().toISOString()
        }
      });
    } catch (err) {
      res.status(500).json({ status: 'error', error: err.message });
    }
  }
);
```

## Testing

```bash
curl -X POST http://46.225.82.130:9090/agent/upload \
  -H "Authorization: Bearer dytto-agent-token-v1" \
  -F "file=@/path/to/document.pdf" \
  -F "user_id=perscholas" \
  -F "agent_type=fundfish"
```

## Once Implemented

Update Render backend `workspace.py` to proxy uploads:
```python
# Instead of saving to Render, proxy to Hetzner
async with httpx.AsyncClient() as client:
    files = {'file': (file.filename, file_content, file.content_type)}
    data = {'user_id': org_id, 'agent_type': 'fundfish'}
    
    response = await client.post(
        f'{HETZNER_BRIDGE_URL}/agent/upload',
        files=files,
        data=data,
        headers={'Authorization': f'Bearer {HETZNER_TOKEN}'},
        timeout=30.0
    )
    
    return response.json()
```
