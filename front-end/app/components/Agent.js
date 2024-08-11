import Message from './Message';
import { useState, useEffect } from 'react';
import Accordion from 'react-bootstrap/Accordion';
import Badge from 'react-bootstrap/Badge';
import config from '../config.js';

const Agent = ({ agent, refreshDataset }) => {
  const [messages, setMessages] = useState(agent.message_set);
  const [userInput, setUserInput] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [loadingMessage, setLoadingMessage] = useState("Working...");

  useEffect(() => {
    setIsLoading(true);
    console.log('triggered useffect');
    console.log(agent.id);
    console.log(agent.completed_at);
    if (agent.completed_at) { 
      setIsLoading(false);
    } 
    setMessages(agent.message_set); // Update messages if the agent prop changes
  }, [agent]);

  useEffect(() => {
    if (agent.completed_at === null) { 
      setIsLoading(true);
      console.log('running this only once when component is loaded if completed_at is null');
      console.log(agent.completed_at);
      fetchNextMessage();
    }
  }, []);

  const formatTableIDs = (ids) => {
    if (!ids || !ids.length) return "[Deleted table(s)]";
    const prefix = ids.length === 1 ? "(Table ID " : "(Table IDs ";
    return prefix + ids.join(", ") + ")";
  }

  const fetchNextMessage = async () => {
    try {
      setIsLoading(true);
      const response = await fetch(`${config.baseApiUrl}/agents/${agent.id}/next_message`);
      const data = await response.json();
      console.log(agent);
      await refreshDataset();
      console.log(data);
      console.log(agent);

      if (data.agent === null) { // Either the agent is completed, or there is no next message because we require user input
        setIsLoading(false);
      } else {
        console.log('there is a next message, add it to the others then call next message again')
        setMessages(prevMessages => [...prevMessages, data]);
        fetchNextMessage(); // Keep fetching next messages until done
      }
    } catch (error) {
      console.error("Error fetching next message:", error);
      setIsLoading(false);
    }
  };

  const handleUserInput = async (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      setIsLoading(true);
      setLoadingMessage("Working...");

      try {
        await fetch(`${config.baseApiUrl}/messages/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content: userInput, role: 'user', agent: agent.id })
        });
        setUserInput("");
        fetchNextMessage(); // Start fetching messages again
      } catch (error) {
        console.error("Error:", error);
        setIsLoading(false);
      }
    }
  };

  return (
    <>
      <Accordion.Item eventKey={agent.id}>
        <Accordion.Header>
          Task: {agent.task.name.replace(/^[-_]*(.)/, (_, c) => c.toUpperCase()).replace(/[-_]+(.)/g, (_, c) => ' ' + c.toUpperCase())} 
          &nbsp;-&nbsp;<small>{formatTableIDs(agent.tables)}</small>
          {agent.completed_at != null && (
            <span>&nbsp;<Badge bg="secondary">complete <i className="bi-check-square"></i></Badge></span>
          )}
          &nbsp;
        </Accordion.Header>
        <Accordion.Body>

        {agent.message_set.filter(function (message) { return message.role != 'system' }).map((message) => (
            <Message key={message.id} message={message} />
          ))}

          {isLoading && (
            <div className="message user-input-loading">
              <div className="d-flex align-items-center">
                <strong>{loadingMessage}</strong>
                <div className="spinner-border ms-auto" role="status" aria-hidden="true"></div>
              </div>
            </div>
          )}
          {!agent.completed_at && !isLoading && (
            <div className="input-group">
              <input type="text" className="form-control user-input" value={userInput} onKeyPress={handleUserInput} onChange={e => setUserInput(e.target.value)} placeholder="Message ChatIPT" />
              <div className="input-group-append"><span className="input-group-text"><i className="bi bi-arrow-up-circle"></i></span></div>
            </div>
          )}
        </Accordion.Body>
      </Accordion.Item>
    </>
  );
};

export default Agent;
