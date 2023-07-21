import Message from './Message';
import { useState } from 'react';

const Agent = ({ agent }) => {
    const [messages, setMessages] = useState(agent.message_set);
    const [isComplete, setIsComplete] = useState(agent.completed !== null);
  
    // function to handle user input
    const handleUserInput = (userMessage) => {
      // add user message to messages list
      setMessages([...messages, { content: userMessage, role: 'user' }]);
  
      // send user message to the backend
      fetch(`http://publishgpt-back.local/api/agents/${agent.id}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: userMessage })
      })
      .then(response => response.json())
      .then(data => {
        if (data.id) {
          // assistant reply received, add it to messages
          setMessages([...messages, { content: data.content, role: 'assistant' }]);
        } else {
          // no reply means the agent has finished its task
          setIsComplete(true);
        }
      });
    };
  
    return (
      <div className={`agent-task ${agent.task} ${isComplete ? 'complete' : ''}`}>
        <h2>{agent.task}</h2>
        <div className="messages">
          {messages.map((message, i) => (
            <Message key={i} role={message.role} content={message.content} />
          ))}
        </div>
        {!isComplete && <input type="text" className="user-input" onChange={e => handleUserInput(e.target.value)} />}
      </div>
    );
  };
  
export default Agent;