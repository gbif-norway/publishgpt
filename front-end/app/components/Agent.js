import Message from './Message';
import { useState, useEffect, useRef } from 'react';
import Accordion from 'react-bootstrap/Accordion';
import Badge from 'react-bootstrap/Badge';
import config from '../config.js';


const Agent = ({ agent, refreshDataset }) => {
  const [userInput, setUserInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState("Working...");

  const handleUserInput = (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      setIsLoading(true);
      setLoadingMessage("Working...");
      const timeoutId = setTimeout(() => { setLoadingMessage("Still working..."); }, 10000);

      fetch(`${config.baseApiUrl}/messages/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: userInput, role: 'user', agent: agent.id })
      })
        .then(response => response.json())
        .then(() => refreshDataset())
        .then(() => { clearTimeout(timeoutId); setIsLoading(false); })
        .catch((error) => {
          console.error("Error:", error);
          clearTimeout(timeoutId);
          setIsLoading(false);
        });

      setUserInput("");
    }
  };

  return (
    <>
      <Accordion.Item eventKey={agent.id}>
        <Accordion.Header>
          Task: {agent.task.name.replace(/^[-_]*(.)/, (_, c) => c.toUpperCase()).replace(/[-_]+(.)/g, (_, c) => ' ' + c.toUpperCase())}
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
            <div className="message assistant-message">
              <div className="d-flex align-items-center">
                <strong>{loadingMessage}</strong>
                <div className="spinner-border ms-auto" role="status" aria-hidden="true"></div>
              </div>
            </div>
          )}
          {!agent.completed_at != null && !isLoading && <input type="text" className="form-control user-input" value={userInput} onKeyPress={handleUserInput} onChange={e => setUserInput(e.target.value)} />}
        </Accordion.Body>
      </Accordion.Item>
    </>
  );
};

export default Agent;
