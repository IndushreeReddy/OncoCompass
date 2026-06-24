import { useState } from 'react'
import { uploadFile } from '../api'
import './UploadForm.css'

export default function UploadForm({ onUploadSuccess }) {
  const [file, setFile] = useState(null)
  const [skipAnnotation, setSkipAnnotation] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState(null)

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0]
    setFile(selectedFile)
    setError(null)

    // Auto-detect: if filename ends with .txt, suggest skipping annotation
    if (selectedFile && selectedFile.name.toLowerCase().endsWith('.txt')) {
      setSkipAnnotation(true)
    } else {
      setSkipAnnotation(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!file) {
      setError('Please select a file')
      return
    }

    setUploading(true)
    setError(null)

    try {
      const result = await uploadFile(file, skipAnnotation)
      if (result && result.job_id) {
        onUploadSuccess(result.job_id)
      } else {
        setError('Upload succeeded but no job ID received')
      }
    } catch (err) {
      // Better error messages
      let errorMessage = 'Upload failed'
      if (err.message) {
        errorMessage = err.message
      } else if (err instanceof TypeError && err.message.includes('fetch')) {
        errorMessage = 'Cannot connect to server. Please check if the backend is running.'
      }
      setError(errorMessage)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="upload-form">
      <h2>Upload VCF File</h2>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="file-input">Select file:</label>
          <input
            id="file-input"
            type="file"
            accept=".vcf,.vcf.gz,.txt"
            onChange={handleFileChange}
            disabled={uploading}
            required
          />
          {file && (
            <p className="file-info">
              Selected: <strong>{file.name}</strong> ({(file.size / 1024 / 1024).toFixed(2)} MB)
            </p>
          )}
        </div>

        <div className="form-group">
          <label>
            <input
              type="checkbox"
              checked={skipAnnotation}
              onChange={(e) => setSkipAnnotation(e.target.checked)}
              disabled={uploading}
            />
            Skip annotation (file is already annotated)
          </label>
          <p className="help-text">
            Check this if your file is already annotated with VEP. Files ending in .txt are assumed to be annotated.
          </p>
        </div>

        {error && <div className="error-message">{error}</div>}

        <button type="submit" disabled={uploading || !file} className="submit-button">
          {uploading ? 'Uploading...' : 'Upload and Process'}
        </button>
      </form>
    </div>
  )
}
