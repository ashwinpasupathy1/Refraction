import { useRef, useState, DragEvent, ChangeEvent } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:7331';

interface FileUploadProps {
  onUploaded: (path: string, filename: string) => void;
}

export function FileUpload({ onUploaded }: FileUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [status, setStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle');
  const [filename, setFilename] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  async function upload(file: File) {
    setStatus('uploading');
    setErrorMsg(null);

    const form = new FormData();
    form.append('file', file);

    try {
      const res = await fetch(`${API_BASE}/upload`, {
        method: 'POST',
        body: form,
      });
      const data = await res.json();
      if (data.ok && data.path) {
        setFilename(file.name);
        setStatus('success');
        onUploaded(data.path, file.name);
      } else {
        setErrorMsg(data.error ?? 'Upload failed');
        setStatus('error');
      }
    } catch (e) {
      setErrorMsg(String(e));
      setStatus('error');
    }
  }

  function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    const file = files[0];
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (ext !== 'xlsx' && ext !== 'xls') {
      setErrorMsg('Please upload an .xlsx or .xls file');
      setStatus('error');
      return;
    }
    upload(file);
  }

  function onDragOver(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragging(true);
  }

  function onDragLeave() {
    setDragging(false);
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragging(false);
    handleFiles(e.dataTransfer.files);
  }

  function onChange(e: ChangeEvent<HTMLInputElement>) {
    handleFiles(e.target.files);
  }

  function clearFile() {
    setFilename(null);
    setStatus('idle');
    setErrorMsg(null);
    if (inputRef.current) inputRef.current.value = '';
  }

  if (status === 'success' && filename) {
    return (
      <div
        className="uploaded-file"
        onClick={clearFile}
        title="Click to replace"
      >
        <span>📄</span>
        <span className="uploaded-file-name">{filename}</span>
        <span className="uploaded-file-clear" title="Remove">✕</span>
      </div>
    );
  }

  return (
    <>
      <div
        className={`drop-zone${dragging ? ' dragging' : ''}`}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx,.xls"
          onChange={onChange}
        />
        <div className="drop-zone-text">
          <strong>Click or drag &amp; drop</strong>
          {status === 'uploading' ? 'Uploading…' : '.xlsx / .xls'}
        </div>
      </div>
      {status === 'error' && errorMsg && (
        <div className="upload-status error">{errorMsg}</div>
      )}
    </>
  );
}
