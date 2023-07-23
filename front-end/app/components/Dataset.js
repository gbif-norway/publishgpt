import { useEffect, useState, useCallback } from 'react';  // import useCallback
import { useDropzone } from 'react-dropzone';
import Agent from './Agent';

const Dataset = ({ initialDatasetId }) => {
    const [error, setError] = useState(null);
    const [agents, setAgents] = useState([]);
    const [dataset, setDataset] = useState(null); 
  
    // using useCallback so that it doesn't change on each render
    const refreshAgents = useCallback((dataset) => {
      setDataset(dataset);

      fetch(`http://publishgpt-back.local/api/datasets/${dataset.id}/get_or_create_next_agent`)
      .then(response => response.json())
      .then(next_agent => {
        fetch(`http://publishgpt-back.local/api/datasets/${dataset.id}/completed_agents`)
        .then(response => response.json())
        .then(completed_agents => {
          setAgents([...completed_agents, next_agent]);
        });
      });
    }, []); // dependencies array is empty because refreshAgents doesn't depend on any state/props
  
    const onDrop = (acceptedFiles) => {
      setError(null); // reset error
      const file = acceptedFiles[0];
      const formData = new FormData();
      formData.append('file', file);
      
      fetch('http://publishgpt-back.local/api/datasets/', {
        method: 'POST',
        body: formData
      })
      .then(response => response.json())
      .then(data => {
        refreshAgents(data);
      })
      .catch(err => setError(err.message));
    };
  
    // get root props and input props for the dropzone
    const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop });
  
    // fetch dataset and first agent if initialDatasetId is provided
    useEffect(() => {
      if (initialDatasetId) {
        fetch(`http://publishgpt-back.local/api/datasets/${initialDatasetId}`)
        .then(response => response.json())
        .then(data => {
            refreshAgents(data);
        })
        .catch(err => console.log(err.message));
      }
    }, [initialDatasetId]);
  
    return (
      <div>
        {!dataset ? (
          <div className="agent-task initialise">
            <div className="messages">
              <div className="message assistant-message">
                I can help you publish your biodiversity data to <a href="https://gbif.org" target="_blank" rel="noreferrer">gbif.org</a>. Let's start by taking a look at your data file. 
                <div {...getRootProps()} className="file-drop">
                  <input {...getInputProps()} />
                  {
                    isDragActive ?
                      <p>Drop the files here ...</p> :
                      <p>Drag and drop some files here, or click to select files</p>
                  }
                </div>
              </div>
              {error && <div className="message assistant-message assistant-message-error">{error}</div>}
            </div>
          </div>
        ) : (
        <div className="messages"><div className="message assistant-message">
            <h1>Working to publish {dataset.file.split(/\//).pop()} - started on {new Date(dataset.created).toLocaleString()}</h1>
        </div></div>
        )}

        <div id="Agents">
        {agents.map(agent => (
          <Agent key={agent.id} agent={agent} refreshAgents={() => refreshAgents({id: agent.dataset})}/> // pass refreshAgents function to Agent component
        ))}
        </div>
      </div>
    );
  };
  
export default Dataset;
  