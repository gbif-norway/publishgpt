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
  const [agents, setAgents] = useState([]);
  const [activeAgentKey, setActiveAgentKey] = useState(null);
  const [tables, setTables] = useState({});
  const [activeTableId, setActiveTableId] = useState(null);

  const refreshTables = useCallback(async () => {
    try { 
      const data = await fetchData(`${config.baseApiUrl}/api/tables?dataset=${dataset.id}`);
      const updatedData = data.map(item => {
        const df = JSON.parse(item.df_json);
        delete item.df_json;
        return { ...item, df };
      });
      setTables(updatedData); 
      const sortedTables = data.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
      setActiveTableId(sortedTables[0]?.id);
    } catch (err) { console.log(err.message); }
  }, [dataset]);

  const refreshAgents = useCallback(async () => {
    try {
      const agents = await fetchData(`${config.baseApiUrl}/api/agents?dataset=${dataset.id}`);
      console.log('refresh agents called');
      console.log(agents);
      var last_non_complete_agent_index = agents.findIndex(agent => agent.completed_at === null);
      if (last_non_complete_agent_index === -1) {
        setAgents(agents);
        const created = await fetchData(`${config.baseApiUrl}/api/datasets/${dataset.id}/create_next_agent`);
        if (created != null) await refreshAgents();
      } else {
        var visible_agents = agents.slice(0, last_non_complete_agent_index + 1);
        setActiveAgentKey(visible_agents[visible_agents.length - 1].id);
        setAgents(visible_agents);
      }
      await refreshTables(dataset.id);
    } catch (err) { console.log(err.message); }
  }, [dataset, refreshTables]);

  // fetch dataset, first agent and tables if initialDatasetId is provided
  useEffect(() => {
    if (initialDatasetId) {
      const initFetch = async () => {
        try {
          const data = await fetchData(`${config.baseApiUrl}/api/datasets/${initialDatasetId}`);
          setDataset(data);
        } catch (err) { console.log(err.message); }
      };
      initFetch();
    }
  }, [initialDatasetId]);

  useEffect(() => {
    if (dataset) { refreshAgents(); }
  }, [dataset, refreshAgents]);

  return (
    <div>
      {!dataset ? (
      <div className="col-lg-8 mx-auto p-4 py-md-5">
        <div className="agent-task initialise">
          <div className="messages">
            <div className="message assistant-message">
              I can help you publish your biodiversity data to <a href="https://gbif.org" target="_blank" rel="noreferrer">gbif.org</a>. Let's start by taking a look at your data file.
              <FileDrop
                onFileAccepted={(data) => { setDataset(data); }}
                onError={(errorMessage) => setError(errorMessage)}
              />
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
          </div>
          <div className="col-7 sticky-col">
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