import { useState } from 'react'
import UploadForm from './components/UploadForm'
import JobStatus from './components/JobStatus'
import './App.css'

function App() {
  const [jobId, setJobId] = useState(null)

  const handleUploadSuccess = (newJobId) => {
    setJobId(newJobId)
  }

  const handleReset = () => {
    setJobId(null)
  }

  return (
    <div className="App">
      <header className="App-header">
        <h1>OncoCompass</h1>
        <p>Precision Oncology Platform</p>
      </header>
      <main>
        {!jobId ? (
          <UploadForm onUploadSuccess={handleUploadSuccess} />
        ) : (
          <JobStatus jobId={jobId} onReset={handleReset} />
        )}
      </main>
    </div>
  )
}

export default App
