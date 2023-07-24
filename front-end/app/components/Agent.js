import Message from './Message';
import { useState, useEffect, useRef } from 'react';

const Agent = ({ agent, refreshAgents }) => {
    const [messages, setMessages] = useState(agent.message_set);
    const [isComplete, setIsComplete] = useState(agent.completed !== null);
    const [userInput, setUserInput] = useState("");
    const wasComplete = useRef(isComplete);
    const [isLoading, setIsLoading] = useState(false);
    const [loadingMessage, setLoadingMessage] = useState("Working...");
  
    const handleUserInput = (event) => {
      if (event.key === 'Enter') {
        event.preventDefault();
        const updatedMessages = [...messages, { content: userInput, role: 'user', display_to_user: true }];
        setMessages(updatedMessages);

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
                setMessages(data.message_set);
            })
            .catch((error) => {
                console.error("Error:", error);
            });
        }, 5000);
        
        fetch(`http://localhost:8000/api/agents/${agent.id}/chat/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: userInput })
        })
        .then(response => response.json())
        .then(data => {
            if (data.id) {
                setMessages([...updatedMessages, { content: data.content, role: 'assistant' }]);
            } else {
                setIsComplete(true);
            }
            setIsLoading(false);  // stop loading
            clearTimeout(timeoutId);  // clear the timeout
            clearInterval(intervalId);  // clear the interval
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
    
    useEffect(() => {
      if (!wasComplete.current && isComplete) {  // if agent was not complete and is now complete
        refreshAgents(); // call the refreshAgents function
      }
      wasComplete.current = isComplete; // update the previous value of isComplete
    }, [isComplete, refreshAgents]); // add isComplete and refreshAgents to the dependencies array

    // check if there are no messages and task is complete
    if (messages.filter(function(message) { return (message.display_to_user) }).length === 0 && isComplete) {
      return null; // return null to not render anything
    }

    return (
      <div className={`accordion-item agent-task ${agent.task.name} ${isComplete ? 'complete' : ''}`}>
        <h2 className="accordion-header">
          <button className="accordion-button" type="button" data-bs-toggle="collapse" data-bs-target={`#Agent${agent.id}`} aria-expanded="true" aria-controls={`Agent${agent.id}`}>
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
              <div class="d-flex align-items-center">
                <strong>{loadingMessage}</strong>
                <div class="spinner-border ms-auto" role="status" aria-hidden="true"></div>
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
