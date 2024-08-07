import { useEffect, useState, useCallback } from 'react';
import Agent from './Agent';
import FileDrop from './FileDrop';
import Accordion from 'react-bootstrap/Accordion';
import DataTable from 'react-data-table-component';
import Tabs from 'react-bootstrap/Tabs';
import Tab from 'react-bootstrap/Tab';
import config from '../config.js';

const fetchData = async (url, options = {}) => {
  const response = await fetch(url, options);
  if (!response.ok) throw new Error('Network response was not ok');
  return response.json();
};

const Dataset = ({ initialDatasetId }) => {
  const [error, setError] = useState(null);
  const [dataset, setDataset] = useState(null);
  const [activeDatasetID, setActiveDatasetID] = useState(null);
  const [agents, setAgents] = useState([]);
  const [activeAgentKey, setActiveAgentKey] = useState(null);
  const [tables, setTables] = useState([]);
  const [activeTableId, setActiveTableId] = useState(null);

  const refreshTables = useCallback(async () => {
    const tables = await fetchData(`${config.baseApiUrl}/tables?dataset=${activeDatasetID}`);
    var updatedTables = tables.map(item => {
      const df = JSON.parse(item.df_json);
      delete item.df_json;
      return { ...item, df };
    });
    setTables(updatedTables)
    const sortedTables = tables.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
    setActiveTableId(sortedTables[0]?.id);
  }, [activeDatasetID])

  const refreshDataset = useCallback(async () => {
    try {
      const dataset = await fetchData(`${config.baseApiUrl}/datasets/${activeDatasetID}`);
      if(dataset.rejected_at != null || dataset.published_at  != null) {
        var visible_agents = dataset.agent_set;
      } else {
        var last_non_complete_agent_index = dataset.agent_set.findIndex(agent => agent.completed_at === null);
        var visible_agents = dataset.agent_set.slice(0, last_non_complete_agent_index + 1);
      }
      setActiveAgentKey(visible_agents[visible_agents.length - 1].id);
      setAgents(visible_agents);
      refreshTables();
      setDataset(dataset);
    } catch (err) { console.log(err.message); }
  }, [activeDatasetID]);

  useEffect(() => {
    if (initialDatasetId) { setActiveDatasetID(initialDatasetId); }
  }, [initialDatasetId, setActiveDatasetID]);

  useEffect(() => {
    if (activeDatasetID) { refreshDataset();  }
  }, [activeDatasetID, refreshDataset]);

  const CustomTabTitle = ({ children }) => <span dangerouslySetInnerHTML={{ __html: children }} />;

  return (
    <div className="container-fluid">
      {!dataset ? (
      <div className="col-lg-8 mx-auto p-4 py-md-5">
        <div className="agent-task initialise">
          <div className="messages">
            <div className="message assistant-message">
              So, you want to publish some biodiversity data to <a href="https://gbif.org" target="_blank" rel="noreferrer">gbif.org</a>? I can help you with that! Let's start by taking a look at your data file.
              <FileDrop
                onFileAccepted={(data) => { setActiveDatasetID(data); }}
                onError={(errorMessage) => setError(errorMessage)}
              />
            </div>
            {error && <div className="message assistant-message assistant-message-error">{error}</div>}
          </div>
        </div>
      </div>
      ) : (
      <div>
        <div className="row mx-auto p-4 no-bottom-margin no-bottom-padding">
          <div className="col-12">
            <h1>Publishing {dataset.file.split(/\//).pop()} <small>started {new Date(dataset.created_at).toLocaleString()}</small></h1>
            {dataset.title && (<div className="alert alert-info no-bottom-margin" role="alert">Title: {dataset.title}</div>)}
            {dataset.description && (<div className="alert alert-info no-bottom-margin" role="alert">Description: {dataset.description}</div>)}
            {dataset.structure_notes && (<div className="alert alert-info no-bottom-margin" role="alert">Notes about the structure: {dataset.structure_notes}</div>)}            {dataset.rejected_at && (
              <div className="alert alert-warning" role="alert">
                This dataset cannot be published on GBIF as it does not contain occurrence or checklist data. Please try uploading a new dataset.
              </div>
            )}
          </div>
        </div>
        <div className="row mx-auto p-4">
          <div className="col-6">
            {Array.isArray(agents) && agents.length > 0 &&
              <Accordion activeKey={activeAgentKey} onSelect={(key) => setActiveAgentKey(key)}>
                {agents.map(agent => (
                  <Agent key={agent.id} agent={agent} refreshDataset={() => refreshDataset()} />
                ))}
              </Accordion>
            }
          </div>
          <div className="col-6">
            <div className="sticky-top">
              {tables.length > 0 && (
                <Tabs activeKey={activeTableId} onSelect={(k) => setActiveTableId(k)} className="mb-3">
                  {tables.map((table) => (
                    <Tab eventKey={table.id} 
                    title={<CustomTabTitle>{`${table.title} <small>(ID ${table.id})</small>`}</CustomTabTitle>} 
                    key={table.id}>
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
      </div>
      )}
    </div>
  );
};

export default Dataset;