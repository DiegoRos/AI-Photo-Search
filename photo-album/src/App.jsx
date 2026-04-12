import { useState } from 'react'
import './App.css'

function App() {
  const [searchQuery, setSearchBar] = useState('')
  const [photos, setPhotos] = useState([])
  const [selectedFile, setSelectedFile] = useState(null)
  const [customLabels, setCustomLabels] = useState('')

  // Placeholder for GET /search
  const searchPhotos = async (query) => {
    console.log('Searching for:', query)
    // This is where you would call the API Gateway SDK
    // Example: sdk.searchGet({q: query})
    
    // Mocking response for now
    const mockResults = [
      { url: 'https://via.placeholder.com/300', labels: ['dog', 'park'] },
      { url: 'https://via.placeholder.com/301', labels: ['cat', 'home'] },
    ]
    setPhotos(mockResults)
  }

  // Placeholder for PUT /upload
  const uploadPhoto = async (file, labels) => {
    if (!file) {
      alert('Please select a file first!')
      return
    }
    console.log('Uploading file:', file.name)
    console.log('With custom labels:', labels)
    
    // This is where you would call the API Gateway SDK
    // Example: sdk.uploadPut({}, file, {headers: {'x-amz-meta-customLabels': labels}})
    
    alert('Upload triggered! Check console for details.')
  }

  const handleSearch = (e) => {
    e.preventDefault()
    searchPhotos(searchQuery)
  }

  const handleUpload = (e) => {
    e.preventDefault()
    uploadPhoto(selectedFile, customLabels)
  }

  return (
    <div className="container">
      <header>
        <h1>Photo Album</h1>
        
        <form className="search-bar" onSubmit={handleSearch}>
          <input 
            type="text" 
            placeholder="Search photos (e.g., 'show me dogs')" 
            value={searchQuery}
            onChange={(e) => setSearchBar(e.target.value)}
          />
          <button type="submit">Search</button>
        </form>

        <form className="upload-section" onSubmit={handleUpload}>
          <h3>Upload New Photo</h3>
          <div className="upload-inputs">
            <input 
              type="file" 
              accept="image/png, image/jpeg, image/jpg"
              onChange={(e) => setSelectedFile(e.target.files[0])}
            />
            <input 
              type="text" 
              placeholder="Custom labels (comma separated)" 
              value={customLabels}
              onChange={(e) => setCustomLabels(e.target.value)}
            />
          </div>
          <button type="submit">Upload</button>
        </form>
      </header>

      <main>
        {photos.length > 0 ? (
          <div className="photo-grid">
            {photos.map((photo, index) => (
              <div key={index} className="photo-card">
                <img src={photo.url} alt={`Result ${index}`} />
                <div className="photo-info">
                  <div className="labels">
                    {photo.labels.map((label, lIndex) => (
                      <span key={lIndex} className="label">
                        {label}
                        <button 
                          className="delete-label" 
                          onClick={() => {
                            const newLabels = photo.labels.filter((_, i) => i !== lIndex)
                            const newPhotos = [...photos]
                            newPhotos[index].labels = newLabels
                            setPhotos(newPhotos)
                            console.log('Label deleted. New labels:', newLabels)
                          }}
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                  <div className="edit-labels">
                    <input 
                      type="text" 
                      placeholder="Add label..."
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          const newLabel = e.target.value.trim()
                          if (newLabel && !photo.labels.includes(newLabel)) {
                            const newLabels = [...photo.labels, newLabel]
                            const newPhotos = [...photos]
                            newPhotos[index].labels = newLabels
                            setPhotos(newPhotos)
                            e.target.value = ''
                            console.log('Label added. New labels:', newLabels)
                          }
                        }
                      }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p>No photos to show. Try searching!</p>
        )}
      </main>
    </div>
  )
}

export default App
