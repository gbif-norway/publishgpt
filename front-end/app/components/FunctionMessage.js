import { useState } from 'react';
import Button from 'react-bootstrap/Button';
import Collapse from 'react-bootstrap/Collapse';
import TableAssociations from './TableAssociations';
import { CodeBlock, dracula } from "react-code-blocks";


function FunctionMessage({ message }) {
  const [open, setOpen] = useState(false);

  if (!message.content && message.message_table_associations.length === 0) { return null; }
  if (message.function_name == 'SetAgentTaskToComplete') { return null; }
  var content = message.content.replace('` executed, result:', '\n').replace('`', '')

  return (
    <div className={`message function-message`}>
        {message.content && (
          <>
            <Button onClick={() => setOpen(!open)} aria-controls={`collapseFor${message.id}`} aria-expanded={open}>Show work</Button>
            <Collapse in={open}>
              <div id={`collapseFor${message.id}`}>
                <CodeBlock text={content} language="python" theme={dracula} />
              </div>
            </Collapse>
          </>
        )}
        {message.message_table_associations.length > 0 && (
          <TableAssociations key={message.id} associations={message.message_table_associations} />
        )}
    </div>
  );
}

export default FunctionMessage;
