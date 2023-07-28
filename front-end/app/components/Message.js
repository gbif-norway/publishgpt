import FunctionMessage from './FunctionMessage';

const Message = ({ message }) => {
    return (
        <div className="dataset-info-wrapper" id={message.id}>
            {message.role == 'function' ? (
                <FunctionMessage key={message.id} message={message} />
            ) : (
            <div className={`message ${message.role}-message`}>
                <div style={{ whiteSpace: 'pre-wrap' }}>
                    {message.content}
                </div>
            </div>
            )}
        </div>
    );
};

export default Message;  
