/**
 * API client for OncoCompass backend.
 * Uses VITE_API_URL from environment (default: http://localhost:8000)
 */

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Upload a VCF or annotated .txt file
 * @param {File} file - The file to upload
 * @param {boolean} skipAnnotation - Whether to skip VEP annotation
 * @returns {Promise<{job_id: string}>}
 */
export async function uploadFile(file, skipAnnotation = false) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('skip_annotation', skipAnnotation);

  const response = await fetch(`${API_URL}/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Upload failed: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get job status
 * @param {string} jobId - The job ID
 * @returns {Promise<{status: string, progress?: string, error?: string, ...}>}
 */
export async function getJobStatus(jobId) {
  const response = await fetch(`${API_URL}/jobs/${jobId}`);

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error(`Job ${jobId} not found`);
    }
    throw new Error(`Failed to get job status: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Download report for a completed job (PDF, HTML, or TXT)
 * @param {string} jobId - The job ID
 * @returns {Promise<{blob: Blob, filename: string}>}
 */
export async function downloadReport(jobId) {
  const response = await fetch(`${API_URL}/jobs/${jobId}/report`);

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error(`Report not found for job ${jobId}`);
    }
    if (response.status === 409) {
      throw new Error(`Job ${jobId} is not completed yet`);
    }
    throw new Error(`Failed to download report: ${response.statusText}`);
  }

  // Extract filename from Content-Disposition header
  const contentDisposition = response.headers.get('Content-Disposition');
  let filename = `onco_report_${jobId}.pdf`; // fallback
  if (contentDisposition) {
    // Handle both quoted and unquoted filenames
    const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
    if (filenameMatch) {
      filename = filenameMatch[1].replace(/['"]/g, '');
    }
  }

  // Get blob directly - browser will handle MIME type from Content-Type header
  const blob = await response.blob();
  
  return { blob, filename };
}

/**
 * Get report view URL (for opening HTML reports in browser)
 * @param {string} jobId - The job ID
 * @returns {string} URL to view the report
 */
export function getReportViewUrl(jobId) {
  return `${API_URL}/jobs/${jobId}/report/view`;
}
