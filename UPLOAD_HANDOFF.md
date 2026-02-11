# Document Upload Feature - Handoff for PM Agent

**Status:** Backend complete, UI pending

## What's Done ✅

### Hetzner Agent API
- **Endpoint:** `POST http://46.225.82.130:9090/agent/upload`
- **Code:** `/home/dytto-agent/agent-api.js` (line 421-474)
- **Auth:** Bearer `dytto-agent-token-v1`
- **Accepts:** PDF, DOCX, TXT, MD (max 10MB)
- **Storage:** `/home/dytto-agent/workspaces/ff-{org_id}/uploads/{filename}`
- **Status:** ✅ Live and tested

### Render Backend
- **Endpoint:** `POST /api/workspace/upload` (proxies to Hetzner)
- **File:** `backend/routes/workspace.py` (line 440-511)
- **Code:** Validates files, then proxies to Hetzner endpoint
- **Status:** ✅ Deployed

### Frontend API
- **File:** `frontend/src/utils/api.ts`
- **Methods:** `uploadDocument(file)`, `listUploads()`
- **Status:** ✅ Merged

## What's Left ⏳

### 1. Chat UI Upload Button
**File:** `frontend/src/app/chat/page.tsx`

Add before the input box:
```tsx
// File upload state
const [uploading, setUploading] = useState(false)
const [uploadedFiles, setUploadedFiles] = useState([])
const fileInputRef = useRef<HTMLInputElement>(null)

// Load uploaded files
useEffect(() => {
  if (isAuthenticated) {
    api.listUploads().then(res => res.json()).then(data => {
      if (data.files) setUploadedFiles(data.files)
    })
  }
}, [isAuthenticated])

// Handle upload
const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
  const file = e.target.files?.[0]
  if (!file) return
  
  setUploading(true)
  try {
    const response = await api.uploadDocument(file)
    const result = await response.json()
    
    if (result.status === 'success') {
      setUploadedFiles([result.file, ...uploadedFiles])
      // Notify user
      alert(`Uploaded ${result.file.filename}`)
    }
  } catch (err) {
    alert('Upload failed')
  } finally {
    setUploading(false)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }
}

// In JSX, add near input:
<input
  ref={fileInputRef}
  type="file"
  accept=".pdf,.docx,.txt,.md"
  onChange={handleUpload}
  style={{ display: 'none' }}
/>

<button
  onClick={() => fileInputRef.current?.click()}
  disabled={uploading}
  className="p-2 text-gray-600 hover:text-perscholas-primary"
>
  {uploading ? '⏳' : '📎'}
</button>

// File list (show above messages):
{uploadedFiles.length > 0 && (
  <div className="p-4 bg-gray-50 border-b">
    <p className="text-sm font-medium mb-2">Uploaded Files:</p>
    {uploadedFiles.map(f => (
      <div key={f.filename} className="text-xs text-gray-600">
        📄 {f.filename} ({Math.round(f.size / 1024)}KB)
      </div>
    ))}
  </div>
)}
```

### 2. Update Agent TOOLS.md
**File (on Hetzner):** `/home/dytto-agent/templates-fundfish/TOOLS.md`

Add section:
```markdown
## Uploaded Documents

Users can upload documents (PDF, DOCX, TXT, MD) to share context with you.

**Location:** `uploads/` in your workspace

**Check for uploads:**
```bash
ls uploads/
```

**Read uploaded files:**
```bash
cat uploads/document.pdf  # Won't work for PDF
# For PDFs, tell user you see the file but can't read binary formats yet
```

**When to mention:**
- User asks "did you get my file?"
- User uploads a proposal/RFP and asks for help
- User mentions a document by name

**Example:**
User: "I uploaded our RFP template"
You: "I see RFP_template.docx in my workspace. Let me know how I can help with it!"
```

SSH to Hetzner and edit:
```bash
ssh -i ~/.ssh/id_ed25519 root@46.225.82.130
nano /home/dytto-agent/templates-fundfish/TOOLS.md
# Add the section above
# Restart agents: systemctl restart clawdbot-agent
```

### 3. (Optional) Database Table
**File:** Create migration in `backend/migrations/`

```sql
CREATE TABLE workspace_files (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  org_id TEXT NOT NULL,
  filename TEXT NOT NULL,
  file_path TEXT NOT NULL,
  file_size INTEGER NOT NULL,
  uploaded_by UUID REFERENCES auth.users(id),
  uploaded_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_workspace_files_org ON workspace_files(org_id);
```

Run via Supabase SQL Editor.

## Testing

1. **Upload a file:**
```bash
curl -X POST https://capstone-xljm.onrender.com/api/workspace/upload \
  -H "Authorization: Bearer <user_jwt>" \
  -F "file=@/path/to/test.pdf"
```

2. **Check on Hetzner:**
```bash
ssh root@46.225.82.130
ls /home/dytto-agent/workspaces/ff-*/uploads/
```

3. **Chat with agent:**
Ask: "Do you see any uploaded files?"
Agent should check `uploads/` and report.

## Notes

- Files are stored on Hetzner, not Render (persistent)
- Agents need to explicitly check `uploads/` directory
- PDF content extraction requires additional tooling (future work)
- Current limit: 10MB per file

## Ready for Completion

- [ ] Add upload button to chat UI
- [ ] Update TOOLS.md on Hetzner
- [ ] Create database migration (optional)
- [ ] Test end-to-end flow
- [ ] Document in user-facing help

**Time estimate:** 30-60 minutes for UI + TOOLS.md update

---

*Handoff created: 2026-02-11 00:24 EST*
*Backend complete, tested, and deployed*
