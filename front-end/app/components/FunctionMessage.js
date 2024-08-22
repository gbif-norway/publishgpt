import { useState } from 'react';
import Button from 'react-bootstrap/Button';
import Collapse from 'react-bootstrap/Collapse';
import { CodeBlock, dracula } from "react-code-blocks";


function FunctionMessage({ message_content, message_id, is_python }) {
  const [open, setOpen] = useState(false);
  let content = message_content
  if(typeof message_content === 'string') {
    if(message_content.replace(/[ \t\n\r]/gm,'').startsWith('{"code":"')) { 
      console.log('starts with code ' + message_id);
      content = JSON.parse(message_content);
      content = content['code']
    }
  }
  else {
    content = JSON.stringify(content)
  }
  // console.log(content);

  return (
    <>
      <div className='inner-message python'>
        <Button onClick={() => setOpen(!open)} aria-controls={`collapseFor${message_id}`} aria-expanded={open} className={`${is_python ? ("code") : ("results")}`}>
          {is_python ? ("Show generated code") : ("Show code results")}
        </Button>
      </div>
      <div className="inner-function-message">
        <Collapse in={open}>
          <div id={`collapseFor${message_id}`}>
            <CodeBlock text={content} language="python" theme={dracula} />
          </div>
        </Collapse>
      </div>
    </>
  );
}

export default FunctionMessage;
