import { useState } from 'react';

const API_TASKS = ['translate', 'flatten_header', 'drop'] // , 'uncrosstab', 'join_columns', 'split_columns', 'map', 'fix_dates', 'add_basis_of_record'

const IndexPage = () => {
  const [conversation, setConversation] = useState<string[]>([]);
  const [userInput, setUserInput] = useState('');

  const onFileDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();

    // Create dataset in the backend
    const formData = new FormData();
    formData.append('file', e.dataTransfer.files[0]);
    console.log('onFileDrop sent:')
    console.log(formData)
    fetch("http://publishgpt-back.local/datasets/", {
      method: "POST",
      body: formData,
    }).then((response) => {
      if (!response.ok) {
        response.json().then(data => { 
          setConversation(prevState => [...prevState, data['non_field_errors']]);
        })
      } else {
        response.json().then(data => { 
          setConversation(prevState => [...prevState, data['conversations']);
          startChatbot(data['pk'], API_TASKS[0]);
        })
      }
    })
  }

  const startChatbot = (dataset_id: string, task: string) => {
    console.log('starting chatbot...')
    const formData = new FormData();
    formData.append('dataset', dataset_id);
    formData.append('task', task);
    console.log('startChatbot sent:')
    console.log(formData)
    for (var pair of formData.entries()) {
      console.log(pair[0]+ ', ' + pair[1]); 
    }
    fetch("http://publishgpt-back.local/conversations/", {
      method: "POST",
      body: formData,
    }).then((response) => {
      response.json().then(data => {
        if (!response.ok) {
          response.json().then(data => { 
            setConversation(prevState => [...prevState, data['non_field_errors']]);
          })
        } else {
          response.json().then(data => { 
            startChatbot(data['pk'], API_TASKS[0]);
            console.log('startChatbot received:');
            console.log(data);
            setConversation(data['messages']);
          })
        }
      })
    })
  }

  const interact = (action: any, message: string) => {
    console.log('interacting...')
    setConversation(prevState => [...prevState, message]);
    action['messages'].push(message);

    const formData = new FormData();
    formData.append('action', JSON.stringify(action));
    console.log('interacting sent:')
    console.log(formData)
    fetch("http://publishgpt-back.local/actions/", {
      method: "PUT",
      body: formData,
    }).then((response) => {
      response.json().then(data => {
        console.log('interacting received:')
        console.log(data)
        if (data['complete']) {
          callNextStep(action['task'], action['dataset_id']);
        } else {
          const bot_message = data['messages'][data['messages'].length - 1];
          setConversation(prevState => [...prevState, bot_message]);
        }
      })
    })
  }

  const callNextStep = (last_step: string, dataset_id: string) => {
    const next_step = API_TASKS[API_TASKS.findIndex(API_TASKS => API_TASKS === last_step) + 1];
    startChatbot(dataset_id, next_step);
  }

  return (
    <main className="flex flex-col items-center justify-between pb-40">
      <div className="border-gray-200sm:mx-0 mx-5 mt-5 max-w-screen-md rounded-md border sm:w-full">
        <div className="flex flex-col message bot">
          <h1 className="text-lg font-semibold main-header">Hi, I'm PublishGPT</h1>
          <p>
            I can help you publish your biodiversity data to <a href="https://gbif.org" target="_blank" rel="noreferrer">gbif.org</a>. 
            Let's start by taking a look at your csv file. 
            <br />
            <small>It's better if your column headings are descriptive, so I can understand them easily.</small>
          </p>
          <div onDragOver={(e) => e.preventDefault()} onDrop={onFileDrop} className="my-10 w-full h-48 border-2 border-dashed border-gray-400 flex justify-center items-center">
            Drop your CSV here
          </div>
        </div>
        {/* Iterate over messages and insert them here */}
        {conversation.map((message, index) => (
          <div key={index} className={index % 2 === 0 ? 'flex flex-col message bot' : 'flex flex-col message user'}>
            <p>{message}</p>
          </div>
        ))}

        {/* Input field with user message */}
        <input 
          type="text" 
          value={userInput}
          onChange={(e) => setUserInput(e.target.value)}
          onKeyPress={(e) => {
            if (e.key === 'Enter') {
              interact(conversation, userInput);  // assuming conversation is the action object
              setUserInput('');  // clear the input
            }
          }}
        />
      </div>
    </main>
  );
}

export default IndexPage;
