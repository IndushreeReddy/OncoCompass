import { useEffect, useState } from 'react'
import { getJobStatus, downloadReport, getReportViewUrl } from '../api'
import './JobStatus.css'

export default function JobStatus({ jobId, onReset }) {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [downloading, setDownloading] = useState(false)

  // Poll job status every 2-3 seconds
  useEffect(() => {
    if (!jobId) return

    let intervalId
    let isMounted = true

    const pollStatus = async () => {
      try {
        const data = await getJobStatus(jobId)
        if (isMounted) {
          setStatus(data)
          setLoading(false)
          setError(null)

          // Stop polling if job is completed or failed
          if (data.status === 'completed' || data.status === 'failed') {
            if (intervalId) {
              clearInterval(intervalId)
            }
          }
        }
      } catch (err) {
        if (isMounted) {
          // Better error handling
          let errorMessage = err.message || 'Failed to get job status'
          if (err.message && err.message.includes('not found')) {
            errorMessage = `Job ${jobId} not found. It may have been deleted or never existed.`
          } else if (err instanceof TypeError && err.message.includes('fetch')) {
            errorMessage = 'Cannot connect to server. Please check if the backend is running.'
          }
          setError(errorMessage)
          setLoading(false)
          if (intervalId) {
            clearInterval(intervalId)
          }
        }
      }
    }

    // Initial poll
    pollStatus()

    // Set up polling interval (every 2.5 seconds)
    intervalId = setInterval(pollStatus, 2500)

    // Cleanup
    return () => {
      isMounted = false
      if (intervalId) {
        clearInterval(intervalId)
      }
    }
  }, [jobId])

  const handleDownload = async () => {
    if (!jobId) return

    setDownloading(true)
    setError(null)

    try {
      const { blob, filename } = await downloadReport(jobId)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      a.style.display = 'none' // Hide the link
      document.body.appendChild(a)
      a.click()
      // Clean up after a short delay to ensure download starts
      setTimeout(() => {
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
      }, 100)
    } catch (err) {
      // Better error messages for download
      let errorMessage = 'Download failed'
      if (err.message) {
        if (err.message.includes('not completed')) {
          errorMessage = 'Report is not ready yet. Please wait for the job to complete.'
        } else if (err.message.includes('not found')) {
          errorMessage = 'Report file not found. The job may have failed or the report was not generated.'
        } else {
          errorMessage = err.message
        }
      } else if (err instanceof TypeError && err.message.includes('fetch')) {
        errorMessage = 'Cannot connect to server. Please check if the backend is running.'
      }
      setError(errorMessage)
    } finally {
      setDownloading(false)
    }
  }

  const getStatusDisplay = () => {
    if (loading) {
      return { text: 'Loading...', className: 'status-loading' }
    }

    if (error) {
      return { text: `Error: ${error}`, className: 'status-error' }
    }

    if (!status) {
      return { text: 'Unknown', className: 'status-unknown' }
    }

    switch (status.status) {
      case 'pending':
        return { text: 'Pending', className: 'status-pending' }
      case 'running':
        return { text: 'Running', className: 'status-running' }
      case 'completed':
        return { text: 'Completed', className: 'status-completed' }
      case 'failed':
        return { text: 'Failed', className: 'status-failed' }
      default:
        return { text: status.status, className: 'status-unknown' }
    }
  }

  const statusDisplay = getStatusDisplay()

  return (
    <div className="job-status">
      <h2>Job Status</h2>
      <div className="job-info">
        <p className="job-id">Job ID: <code>{jobId}</code></p>
      </div>

      <div className={`status-badge ${statusDisplay.className}`}>
        {statusDisplay.text}
      </div>

      {status?.progress && (
        <div className="progress-message">
          <p>{status.progress}</p>
        </div>
      )}

      {status?.tmb && (
        <div className="tmb-info">
          <h3>Tumor Mutational Burden (TMB)</h3>
          <p><strong>{status.tmb.tmb}</strong> mutations/Mb</p>
          <p>Mutation count: {status.tmb.mutation_count}</p>
        </div>
      )}

      {status?.variant_count !== undefined && (
        <div className="variant-info">
          <p>Filtered variants: <strong>{status.variant_count}</strong></p>
        </div>
      )}

      {status?.status === 'completed' && (
        <div className="download-section">
          <button
            onClick={() => window.open(getReportViewUrl(jobId), '_blank')}
            className="view-button"
            style={{ marginRight: '10px' }}
          >
            View Report (HTML)
          </button>
          <button
            onClick={handleDownload}
            disabled={downloading}
            className="download-button"
          >
            {downloading ? 'Downloading...' : 'Download Report'}
          </button>
        </div>
      )}

      {status?.status === 'failed' && status?.error && (
        <div className="error-section">
          <p className="error-message">Error: {status.error}</p>
        </div>
      )}

      {error && (
        <div className="error-section">
          <p className="error-message">{error}</p>
        </div>
      )}

      <div className="actions">
        <button onClick={onReset} className="reset-button">
          Upload Another File
        </button>
      </div>
    </div>
  )
}
