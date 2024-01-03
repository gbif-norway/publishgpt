import FunctionMessage from './FunctionMessage';

const Message = ({ message }) => {
    return (
        <div className="dataset-info-wrapper" id={message.id}>
            {(message.role == 'function') ? (
                <FunctionMessage key={message.id} message={message} />
            ) : (
            <div className={`message ${message.role}-message`}>
                <div className="avatar">
                    <img src={`http://localhost:8000/static/images/${message.role === 'assistant' ? 'bot.png' : 'user.png'}`}></img>
                </div>
                <div className="message-content" style={{ whiteSpace: 'pre-wrap' }}>
                    {message.content}
                </div>
            </div>
            )}
        </div>
    );
};

export default Message;  
