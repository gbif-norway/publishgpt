import { useState } from 'react';
import Button from 'react-bootstrap/Button';
import Collapse from 'react-bootstrap/Collapse';
import { CodeBlock, dracula } from "react-code-blocks";


function FunctionMessage({ message }) {
  const [open, setOpen] = useState(false);

  var content = message.openai_obj.content.replace('` executed, result:', '\n').replace('`', '')

  return (
    <>
      <div className={`inner-message ${message.openai_obj.function_name}`}>
        <Button onClick={() => setOpen(!open)} aria-controls={`collapseFor${message.id}`} aria-expanded={open}>Show work</Button>
      </div>
      <div className="inner-function-message">
        <Collapse in={open}>
          <div id={`collapseFor${message.id}`}>
            <CodeBlock text={content} language="python" theme={dracula} />
          </div>
        </Collapse>
      </div>
    </>
  );
}

export default FunctionMessage;
