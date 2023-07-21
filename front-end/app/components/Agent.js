import Message from './Message';
import { useState } from 'react';

const Agent = ({ agent }) => {
    const [messages, setMessages] = useState(agent.message_set);
    const [isComplete, setIsComplete] = useState(agent.completed !== null);
  
    const handleUserInput = (userMessage) => {
      setMessages([...messages, { content: userMessage, role: 'user' }]);
  
      fetch(`http://publishgpt-back.local/api/agents/${agent.id}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: userMessage })
      })
      .then(response => response.json())
      .then(data => {
        if (data.id) {
          setMessages([...messages, { content: data.content, role: 'assistant' }]);
        } else {
          setIsComplete(true);
        }
      });
    };
  
    return (
      <div className={`agent-task ${agent.task} ${isComplete ? 'complete' : ''}`}>
        <h2>{agent.task}</h2>
        <div className="messages">
          {messages.filter(function(message) { return (message.role == 'assistant' | message.role == 'user') }).map((message, i) => (
            <Message key={i} role={message.role} content={message.content} />
          ))}
        </div>
        {!isComplete && <input type="text" className="user-input" onChange={e => handleUserInput(e.target.value)} />}
      </div>
    );
  };
  
export default Agent;