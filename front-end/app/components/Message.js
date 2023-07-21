const Message = ({ role, content }) => (
    <div className={`message ${role}-message`}>{content}</div>
  );

export default Message;  