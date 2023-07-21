const Message = ({ role, content }) => (
    <div className={`message ${role}-message`}><code>{content}</code></div>
  );

export default Message;  