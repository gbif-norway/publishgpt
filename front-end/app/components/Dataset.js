import { useEffect, useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import Agent from './Agent';
import Accordion from 'react-bootstrap/Accordion';
import DataTable from 'react-data-table-component';
import Tabs from 'react-bootstrap/Tabs';
import Tab from 'react-bootstrap/Tab';
import config from '../config.js';


const Dataset = ({ initialDatasetId }) => {
  console.log(config.baseApiUrl);
  console.log(process.env);
  const [error, setError] = useState(null);
  const [agents, setAgents] = useState([]);
  const [dataset, setDataset] = useState(null);
  const [tables, setTables] = useState([]);
  const [activeTableId, setActiveTableId] = useState(null);
  const [tableData, setTableData] = useState([]);
  const [tableColumns, setTableColumns] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState("Working...");
  const [activeAgentKey, setActiveAgentKey] = useState(null);

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


  // fetch dataset and first agent if initialDatasetId is provided
  useEffect(() => {
    if (initialDatasetId) {
      fetch(`${config.baseApiUrl}/api/datasets/${initialDatasetId}`)
        .then(response => response.json())
        .then(data => {
          setDataset(data);
          setTables(data.table_set);
          const mostRecentTable = data.table_set[0]; // Assuming table_set is ordered by updated_at DESC
          setActiveTableId(mostRecentTable.id);
          fetchTableData(mostRecentTable.id);
        })
        .catch(err => console.log(err.message));
    }
  }, [initialDatasetId]);


  const fetchTableData = useCallback((tableId) => {
    fetch(`${config.baseApiUrl}/api/tables/${tableId}`)
      .then(response => response.json())
      .then(df => {
        const df_json = JSON.parse(df.df_json);
        const columns = Object.keys(df_json[0]).map((column) => ({
          name: column,
          selector: row => row[column],
          sortable: true,
        }));
        setTableColumns(columns);
        setTableData(df_json);
      })
      .catch(err => console.log(err.message));
  }, []);

  useEffect(() => {
    if (activeTableId) {
      fetchTableData(activeTableId);
    }
  }, [activeTableId, fetchTableData]);

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
    if (dataset) {
      refreshAgents();
    }
  }, [dataset, refreshAgents]);

  // get root props and input props for the dropzone
  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop });

  const darkThemeStyles = {
      rows: {
        style: {
          minHeight: '72px', // override the row height
          backgroundColor: '#333', // dark row background
          color: '#FFF', // text color
        },
      },
      headCells: {
        style: {
          paddingLeft: '8px', // override the cell padding for head cells
          paddingRight: '8px',
          backgroundColor: '#555', // dark head cell background
          color: '#FFF', // text color
        },
      },
      cells: {
        style: {
          paddingLeft: '8px', // override the cell padding for cells
          paddingRight: '8px',
          backgroundColor: '#333', // dark cell background
          color: '#FFF', // text color
        },
      },
      pagination: {
        style: {
          backgroundColor: '#333', // dark background for pagination
          color: '#FFF', // text color
        },
        pageButtonsStyle: {
          backgroundColor: '#555', // button background
          minHeight: '40px', // button height, increase if necessary
          minWidth: '40px', // button width, increase if necessary
          borderRadius: '50%', // button border radius
          margin: '0px 5px', // margin between buttons
          cursor: 'pointer', // cursor type
          '&:hover': {
            backgroundColor: '#666', // hover background color
          },
          '&:disabled': {
            cursor: 'not-allowed', // cursor type when disabled
            backgroundColor: '#333', // background when disabled
            color: '#777', // text color when disabled
          },
        },
      },
    };
  

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
                  <Agent key={agent.id} agent={agent} refreshAgents={() => refreshAgents()} />
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
                    <DataTable columns={tableColumns} data={tableData} customStyles={darkThemeStyles} pagination dense />
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
