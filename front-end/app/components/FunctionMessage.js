import { useState } from 'react';
import Button from 'react-bootstrap/Button';
import Collapse from 'react-bootstrap/Collapse';
import { CodeBlock, dracula } from "react-code-blocks";


function FunctionMessage({ message }) {
  const [open, setOpen] = useState(false);

  if (!message.content) { return null; }
  if (message.function_name == 'SetAgentTaskToComplete') { return null; }
  var content = message.content.replace('` executed, result:', '\n').replace('`', '')

  return (
    <div className={`message function-message`}>
        {message.content && (
          <>
            <div className="inner-message">
              <Button onClick={() => setOpen(!open)} aria-controls={`collapseFor${message.id}`} aria-expanded={open}>Show work</Button>
              <Collapse in={open}>
                <div id={`collapseFor${message.id}`}>
                  <CodeBlock text={content} language="python" theme={dracula} />
                </div>
              </Collapse>
              </div>
          </>
        )}
    </div>
  );
}

export default FunctionMessage;
