import Message from './Message';
import { useState, useEffect, useRef } from 'react';
import Accordion from 'react-bootstrap/Accordion';
import Badge from 'react-bootstrap/Badge';
import TableAssociations from './TableAssociations';


const Agent = ({ agent, refreshAgents }) => {
    const [messages, setMessages] = useState(agent.message_set);
    const [isComplete, setIsComplete] = useState(agent.completed_at !== null);
    const [userInput, setUserInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [loadingMessage, setLoadingMessage] = useState("Working...");

    const updateMessages = async () => {
      try {
        const response = await fetch(`http://localhost:8000/api/agents/${agent.id}/`);
        const data = await response.json();
        setMessages(data.message_set);
      } catch (error) {
        console.error("Error:", error);
      }
    };

    const getNextMessage = () => {
      return new Promise((resolve, reject) => {
        fetch(`http://localhost:8000/api/agents/${agent.id}/next_agent_message`)
          .then(response => response.json())
          .then(data => {
            updateMessages().then(resolve);
            if (data.id && data.function_name == "SetAgentTaskToComplete") {
              console.log('Setting is complete and calling refreshAgents');
              setIsComplete(true);
              refreshAgents();
            }
          })
          .catch(reject);
      });
    }

    const handleUserInput = (event) => {
      if (event.key === 'Enter') {
        event.preventDefault();
        setIsLoading(true);
        setLoadingMessage("Working...");
        const timeoutId = setTimeout(() => { setLoadingMessage("Still working..."); }, 10000);  
        
        fetch(`http://localhost:8000/api/messages/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: userInput, role: 'user', agent: agent.id })
        })
        .then(response => response.json())
        .then(() => updateMessages())
        .then(() => getNextMessage())
        .then(() => { clearTimeout(timeoutId); setIsLoading(false); })
        .catch((error) => {
            console.error("Error:", error);
            clearTimeout(timeoutId);
            setIsLoading(false);
        });

        setUserInput("");
      }
    };

    useEffect(() => {
      setIsLoading(true);
      setLoadingMessage("Working...");
      const timeoutId = setTimeout(() => { setLoadingMessage("Still working..."); }, 10000);  
      updateMessages()
        .then(() => getNextMessage())
        .then(() => { clearTimeout(timeoutId); setIsLoading(false); console.log(messages); })
    }, []); 

    return (
      <>
        <Accordion.Item eventKey={agent.id}>
          <Accordion.Header>
            {agent.id} / Task: {agent.task.name.replace(/^[-_]*(.)/, (_, c) => c.toUpperCase()).replace(/[-_]+(.)/g, (_, c) => ' ' + c.toUpperCase())}
            {isComplete && (
            <span>&nbsp;<Badge bg="secondary">complete <i className="bi-check-square"></i></Badge></span>
            )}
            &nbsp;
            <TableAssociations key={messages[0].id} associations={messages[0].message_table_associations} />
          </Accordion.Header>
          <Accordion.Body>

          {messages.filter(function(message) { return message.role != 'system' }).map((message) => (
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
          {!isComplete && !isLoading && <input type="text" className="form-control user-input" value={userInput} onKeyPress={handleUserInput} onChange={e => setUserInput(e.target.value)} />}
          </Accordion.Body>
        </Accordion.Item>
      </>
    );
  };
  
export default Agent;
