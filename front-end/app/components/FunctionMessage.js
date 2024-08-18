import { useState } from 'react';
import Button from 'react-bootstrap/Button';
import Collapse from 'react-bootstrap/Collapse';
import { CodeBlock, dracula } from "react-code-blocks";


function FunctionMessage({ message_content, message_id }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <div className='inner-message python'>
        <Button onClick={() => setOpen(!open)} aria-controls={`collapseFor${message_id}`} aria-expanded={open}>Show work</Button>
      </div>
      <div className="inner-function-message">
        <Collapse in={open}>
          <div id={`collapseFor${message_id}`}>
            <CodeBlock text={message_content} language="python" theme={dracula} />
          </div>
        </Collapse>
      </div>
    </>
  );
}

export default FunctionMessage;
