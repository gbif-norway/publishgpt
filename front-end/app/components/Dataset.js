import { useEffect, useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import Agent from './Agent';
import Accordion from 'react-bootstrap/Accordion';
import DataTable from 'react-data-table-component';
import Tabs from 'react-bootstrap/Tabs';
import Tab from 'react-bootstrap/Tab';
import config from '../config.js';

const Dataset = ({ initialDatasetId }) => {
  const [error, setError] = useState(null);
  const [dataset, setDataset] = useState(null);
  const [agents, setAgents] = useState([]);
  const [activeAgentKey, setActiveAgentKey] = useState(null);
  const [tables, setTables] = useState({});
  const [activeTableId, setActiveTableId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState("Working...");

  const refreshTables = useCallback(() => {
    fetch(`${config.baseApiUrl}/api/tables?dataset=${dataset.id}`)
    .then(response => response.json())
    .then(data => { 
      const updatedData = data.map(item => {
        const df = JSON.parse(item.df_json);
        delete item.df_json;
        return { ...item, df };
      });
      setTables(updatedData); 
      const sortedTables = data.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
      setActiveTableId(sortedTables[0]?.id);
    })
    .catch(err => console.log(err.message));
  }, [dataset]);

  const refreshAgents = useCallback(() => {
    return fetch(`${config.baseApiUrl}/api/agents?dataset=${dataset.id}`)
      .then(response => response.json())
      .then(agents => {
        console.log('refresh agents called');
        console.log(agents);
        var last_non_complete_agent_index = agents.findIndex(agent => agent.completed_at === null);
        if (last_non_complete_agent_index === -1) {
          setAgents(agents);
          return fetch(`${config.baseApiUrl}/api/datasets/${dataset.id}/create_next_agent`)
            .then(response => response.json())
            .then(created => {
              if (created == null) { console.log('ALL TASKS COMPLETE'); }
              else { return refreshAgents(); }
            })
        }
        else {
          var visible_agents = agents.slice(0, last_non_complete_agent_index + 1);
          setIsLoading(false);
          setActiveAgentKey(visible_agents[visible_agents.length - 1].id);
          setAgents(visible_agents);
        }
        refreshTables(dataset.id);
      });
  }, [dataset]);

  useEffect(() => {
    if (isLoading) {
      const timer = setTimeout(() => {
        setLoadingMessage("Still working...");
      }, 5000);

      const interval = setInterval(() => {
        refreshAgents(dataset.id);
      }, 3000);

      return () => {
        clearTimeout(timer);
        clearInterval(interval);
      };
    } else {
      setLoadingMessage("Working...");
    }
  }, [isLoading, refreshAgents, dataset]);

  // fetch dataset, first agent and tables if initialDatasetId is provided
  useEffect(() => {
    if (initialDatasetId) {
      fetch(`${config.baseApiUrl}/api/datasets/${initialDatasetId}`)
        .then(response => response.json())
        .then(data => { setDataset(data); })
        .then(() => { refreshTables(); })
        .catch(err => console.log(err.message));
    }
  }, [initialDatasetId]);

  const onDrop = (acceptedFiles) => {
    setError(null); // reset error
    const file = acceptedFiles[0];
    const formData = new FormData();
    formData.append('file', file);
    fetch(`${config.baseApiUrl}/api/datasets/`, {
      method: 'POST',
      body: formData
    })
      .then(response => response.json())
      .then(data => {
        setDataset(data);
      })
      .then(() => refreshAgents())
      .catch(err => setError(err.message));
  };

  useEffect(() => {
    if (dataset) { refreshAgents(); }
  }, [dataset, refreshAgents]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop });

  return (
    <div>
      {!dataset ? (
      <div className="col-lg-8 mx-auto p-4 py-md-5">
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
      </div>
      ) : (
      <div>
        <div className="row mx-auto p-4">
          <div className="col-12">
            <h1>Working to publish {dataset.file.split(/\//).pop()} - started on {new Date(dataset.created_at).toLocaleString()}</h1>
          </div>
        </div>
        <div className="row mx-auto p-4">
          <div className="col-5">
            {Array.isArray(agents) && agents.length > 0 &&
              <Accordion activeKey={activeAgentKey} onSelect={(key) => setActiveAgentKey(key)}>
                {agents.map(agent => (
                  <Agent key={agent.id} agent={agent} refreshAgents={() => refreshAgents()} refreshTables={() => refreshTables()} />
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
          <div className="col-7">
            {tables.length > 0 && (
              <Tabs activeKey={activeTableId} onSelect={(k) => setActiveTableId(k)} className="mb-3">
                {tables.map((table) => (
                  <Tab eventKey={table.id} title={table.title} key={table.id}>
                    <DataTable 
                      columns={table.df[0] ? Object.keys(table.df[0]).map(column => ({
                        name: column,
                        selector: row => row[column],
                        sortable: true,
                      })) : []}
                      data={table.df} 
                      theme="dark"
                      pagination 
                      dense 
                    />
                  </Tab>
                ))}
              </Tabs>
            )}
          </div>
        </div>
      </div>
      )}
    </div>
  );
};

export default Dataset;