const Message = ({ role, content }) => (
    <div className={`message ${role}-message`}>
        <div style={{ whiteSpace: 'pre-wrap' }}>
            {content}
        </div>
    </div>
  );

export default Message;  