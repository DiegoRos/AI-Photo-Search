import { useState } from 'react'
import './App.css'

// Initialize API Gateway SDK
// Using a lazy initializer to ensure window.apigClientFactory is available
const getApigClient = () => {
  if (window.apigClientFactory) {
    return window.apigClientFactory.newClient({
      apiKey: '' // If you have an API Key, put it here
    });
  }
  return null;
};

const apigClient = getApigClient();

function App() {
  const [searchQuery, setSearchBar] = useState('')
  const [photos, setPhotos] = useState([])
  const [selectedFile, setSelectedFile] = useState(null)
  const [customLabels, setCustomLabels] = useState('')

  // Search photos using the SDK
  const searchPhotos = async (query) => {
    if (!query) return;
    if (!apigClient) {
      console.error("SDK not loaded");
      return;
    }
    console.log('Searching for:', query);
    
    try {
      const params = { q: query };
      const body = {};
      const additionalParams = {};

      const result = await apigClient.searchGet(params, body, additionalParams);
      console.log('Search result:', result);
      
      // Extract photos from result.data.results (based on Swagger definition)
      const results = result.data.results || [];
      setPhotos(results);
    } catch (error) {
      console.error("Search failed:", error);
      alert("Search failed. Check console for details.");
    }
  };

  // Upload photo using the SDK
  const uploadPhoto = async (file, labels) => {
    if (!file) return;
    if (!apigClient) {
      console.error("SDK not loaded");
      alert("SDK not loaded. Refresh the page.");
      return;
    }
    console.log('Uploading file:', file.name);

    try {
      const params = {
        item: file.name
      };
      const body = file; // The binary file blob
      const additionalParams = {
        headers: {
          'Content-Type': file.type,
          'x-amz-meta-customlabels': labels
        }
      };

      const result = await apigClient.uploadPut(params, body, additionalParams);
      console.log('Upload result:', result);
      if (result.status === 200) {
        alert('Upload successful!');
        setCustomLabels('');
        setSelectedFile(null);
      }
    } catch (error) {
      console.error("Upload failed:", error);
      alert("Upload failed. Check console for details.");
    }
  };

  const handleClear = () => {
    setSearchBar('')
    setPhotos([])
    setSelectedFile(null)
    setCustomLabels('')
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
          <button type="button" onClick={handleClear} className="secondary">Clear</button>
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
