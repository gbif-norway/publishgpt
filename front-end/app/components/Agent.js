import Message from './Message';
import { useState, useEffect, useRef } from 'react';  // import useRef

const Agent = ({ agent, refreshAgents }) => {
    const [messages, setMessages] = useState(agent.message_set);
    const [isComplete, setIsComplete] = useState(agent.completed !== null);
    const [userInput, setUserInput] = useState("");
    const wasComplete = useRef(isComplete); // create a ref to store the previous value of isComplete
  
    const handleUserInput = (event) => {
      console.log(messages);
      if (event.key === 'Enter') {
        setMessages([...messages, { content: userInput, role: 'user' }]);
    
        fetch(`http://publishgpt-back.local/api/agents/${agent.id}/chat/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content: userInput })
        })
        .then(response => response.json())
        .then(data => {
          if (data.id) {
            setMessages([...messages, { content: data.content, role: 'assistant' }]);
          } else {
            setIsComplete(true);
          }
        });
        setUserInput("");
        event.preventDefault();
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
          </div>
        </div>
        {!isComplete && <input type="text" className="form-control user-input" value={userInput} onKeyPress={handleUserInput} onChange={e => setUserInput(e.target.value)} />}
      </div>
    );
  };
  
export default Agent;
