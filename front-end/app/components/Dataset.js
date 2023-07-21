import { useEffect, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import Agent from './Agent';

const Dataset = ({ initialDatasetId }) => {
    const [dataset, setDataset] = useState(null);
    const [error, setError] = useState(null);
    const [agents, setAgents] = useState([]);
  
    // fetch next agent
    const fetchNextAgent = (dataset) => {
        console.log(dataset);
      fetch(`http://publishgpt-back.local/api/datasets/${dataset.id}/get_or_create_next_agent`)
      .then(response => response.json())
      .then(data => {
        console.log('test');
        console.log(data);
        console.log('test');
        setAgents([...agents, data]);
      });
    };
  
    // handle file drop
    const onDrop = (acceptedFiles) => {
      console.log('file drop');
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
        console.log(data);
        setDataset(data);
        fetchNextAgent(data);
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
          console.log('testb');
          console.log(data);
          setDataset(data);
          fetchNextAgent(data);
        })
        .catch(err => console.log(err.message));
      }
    }, [initialDatasetId]);
  
    return (
      <div>
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
  
        {agents.map(agent => (
          <Agent key={agent.id} agent={agent} />
        ))}
      </div>
    );
  };
  
export default Dataset;
  