import { useEffect, useState, useCallback } from 'react';  
import { useDropzone } from 'react-dropzone';
import Agent from './Agent';
import Accordion from 'react-bootstrap/Accordion';

const Dataset = ({ initialDatasetId }) => {
    const [error, setError] = useState(null);
    const [agents, setAgents] = useState([]);
    const [dataset, setDataset] = useState(null); 
    const [isLoading, setIsLoading] = useState(false);
    const [loadingMessage, setLoadingMessage] = useState("Working...");
    const [activeAgentKey, setActiveAgentKey] = useState(null);

    const fetchCompletedAgents = useCallback((datasetId) => {
      return fetch(`http://localhost:8000/api/datasets/${datasetId}/completed_agents`)
        .then(response => response.json())
        .then(completed_agents => {
          setAgents(completed_agents);
        });
    }, []);

    const refreshAgents = useCallback(() => {
      setIsLoading(true);
      fetchCompletedAgents(dataset.id)
      .then(() => {
        fetch(`http://localhost:8000/api/datasets/${dataset.id}/get_or_create_next_agent`)
          .then(response => response.json())
          .then(next_agent => { 
            setAgents(prevAgents => [...prevAgents, next_agent]);
            setIsLoading(false);
            setActiveAgentKey(next_agent.id);
          });
      })
    }, [fetchCompletedAgents, dataset]);

    useEffect(() => {
      if (isLoading) {
        const timer = setTimeout(() => {
          setLoadingMessage("Still working...");
        }, 5000);

        const interval = setInterval(() => {
          fetchCompletedAgents(dataset.id);
        }, 3000);

        return () => {
          clearTimeout(timer);
          clearInterval(interval);
        };
      } else {
        setLoadingMessage("Working...");
      }
    }, [isLoading, fetchCompletedAgents, dataset]);


    // fetch dataset and first agent if initialDatasetId is provided
    useEffect(() => {
      if (initialDatasetId) {
        fetch(`http://localhost:8000/api/datasets/${initialDatasetId}`)
        .then(response => response.json())
        .then(data => {
          setDataset(data);
        })
        .catch(err => console.log(err.message));
      }
    }, [initialDatasetId]);
    
    const onDrop = (acceptedFiles) => {
      setError(null); // reset error
      const file = acceptedFiles[0];
      const formData = new FormData();
      formData.append('file', file);
      
      fetch('http://localhost:8000/api/datasets/', {
        method: 'POST',
        body: formData
      })
      .then(response => response.json())
      .then(data => {
        setDataset(data);
      })
      // .catch(err => setError(err.message));
    };
  
    useEffect(() => {
      if (dataset) {
        refreshAgents();
      }
    }, [dataset, refreshAgents]); 

    // get root props and input props for the dropzone
    const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop });
  
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

        { Array.isArray(agents) && agents.length > 0 && 
          <Accordion activeKey={activeAgentKey} onSelect={(key) => setActiveAgentKey(key)}>
          {agents.map(agent => (
            <Agent key={agent.id} agent={agent} refreshAgents={() => refreshAgents()}/>
          ))}
          </Accordion>
        }

        {isLoading && (
            <div className="message assistant-message">
              <div className="d-flex align-items-center">
                <strong>{loadingMessage}</strong>
                <div className="spinner-border ms-auto" role="status" aria-hidden="true"></div>
              </div>
            </div>
        )}
      </div>
    );
};

export default Dataset;
  