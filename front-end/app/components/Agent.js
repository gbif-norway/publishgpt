import Message from './Message';
import { useState, useEffect, useRef } from 'react';

const Agent = ({ agent, refreshAgents }) => {
    const [messages, setMessages] = useState(agent.message_set);
    const [isComplete, setIsComplete] = useState(agent.completed !== null);
    const [userInput, setUserInput] = useState("");
    const wasComplete = useRef(isComplete);
    const [isLoading, setIsLoading] = useState(false);
    const [loadingMessage, setLoadingMessage] = useState("Working...");

    function fetchWithTimeout(resource, options = {}, timeout = 30000) {
      return Promise.race([
        fetch(resource, options),
        new Promise((_, reject) => 
          setTimeout(() => reject(new Error('Request timed out')), timeout)
        )
      ]);
    }

    const updateMessages = (newData) => {
      const newMessages = [...messages, ...newData];
  
      // Create a Map to eliminate duplicates based on the id
      const uniqueMessagesMap = new Map(newMessages.map(msg => [msg.id, msg]));
  
      // Convert back to an array and sort based on the id
      const uniqueSortedMessages = Array.from(uniqueMessagesMap.values())
          .sort((a, b) => a.id - b.id);
      console.log(uniqueSortedMessages);
      setMessages(uniqueSortedMessages);
    };

    const handleUserInput = (event) => {
      if (event.key === 'Enter') {
        event.preventDefault();
        
        setIsLoading(true);
        setLoadingMessage("Working...");

        // after 10 seconds, change the loading message
        const timeoutId = setTimeout(() => {
            setLoadingMessage("Still working...");
        }, 10000);

        // Set an interval to fetch messages every 5 seconds
        const intervalId = setInterval(() => {
          fetch(`http://localhost:8000/api/agents/${agent.id}/`)
            .then(response => response.json())
            .then(data => {
              updateMessages(data.message_set);
            })
            .catch((error) => {
                console.error("Error:", error);
            });
        }, 5000);
        
        fetch(`http://localhost:8000/api/messages/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: userInput, display_to_user: true, role: 'user', agent: agent.id })
        })
        .then(response => response.json())
        .then(data => {
            console.log(data);
            updateMessages([data]);
            console.log(messages);
            fetch(`http://localhost:8000/api/agents/${agent.id}/next_agent_message`)
            .then(response => response.json())
            .then(data => {
              if (data.id) {
                console.log('agent not yet complete');
                updateMessages([data]);
                console.log(messages);
              } else {
                console.log('setting agent to complete');
                console.log(agent)
                setIsComplete(true);
                refreshAgents();
              }
              setIsLoading(false);  // stop loading
              clearTimeout(timeoutId);  // clear the timeout
              clearInterval(intervalId);  // clear the interval
            })
        })
        .catch((error) => {
            console.error("Error:", error);
            setIsLoading(false);  // stop loading in case of error
            clearTimeout(timeoutId);  // clear the timeout
            clearInterval(intervalId);  // clear the interval
        });

        setUserInput("");
      }
    };
    
    // useEffect(() => {
    //   if (!wasComplete.current && isComplete) {  
    //     refreshAgents({id: agent.dataset.id});
    //   }
    //   wasComplete.current = isComplete; 
    // }, [isComplete, refreshAgents, agent.dataset]); // dependencies array

    // check if there are no messages and task is complete
    if (messages.filter(function(message) { return (message.display_to_user) }).length === 0 && isComplete) {
      return null; // return null to not render anything
    }

    return (
      <div className={`accordion-item agent-task ${agent.task.name} ${isComplete ? 'complete' : ''}`}>
        <h2 className="accordion-header">
          <button className={`accordion-button ${isComplete ? 'collapsed' : ''}`} type="button" data-bs-toggle="collapse" data-bs-target={`#Agent${agent.id}`} aria-expanded="true" aria-controls={`Agent${agent.id}`}>
            Task: {agent.task.name.replace(/^[-_]*(.)/, (_, c) => c.toUpperCase()).replace(/[-_]+(.)/g, (_, c) => ' ' + c.toUpperCase())} {isComplete ? '(complete)' : ''}
          </button>
        </h2>
        <div id={`Agent${agent.id}`} className={`accordion-collapse collapse ${isComplete ? '' : 'show'} messages`}>
          <div className="accordion-body">
          {messages.filter(function(message) { return (message.display_to_user) }).map((message, i) => (
            <Message key={i} role={message.role} content={message.content} />
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
          </div>
        </div>
      </div>
    );
  };
  
export default Agent;
