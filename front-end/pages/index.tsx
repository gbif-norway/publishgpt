import { useState } from 'react';

const IndexPage = () => {
  const [conversation, setConversation] = useState<string[]>([]);
  const [userInput, setUserInput] = useState('');

  const onFileDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();

    // Create dataset in the backend
    const formData = new FormData();
    formData.append('file', e.dataTransfer.files[0]);
    fetch("http://publishgpt-back.local/datasets/", {
      method: "POST",
      body: formData,
    }).then((response) => {
      if (!response.ok) {
        response.json().then(data => { 
          // Show error message in initial-errors div
        })
      } else {
        response.json().then(data => { 
          // Store data['df_sample'] for display later
          // GET 'http://publishgpt-back.local/datasets/' + data['pk'] + '/get_or_create_next_agent/'
          // Results will look like this:
        //   {
        //     "id": 5,
        //     "message_set": [
            //   {
            //     "id": 11,
            //     "created": "2023-07-20T15:32:23.562035Z",
            //     "content": "Some content",
            //     "function_name": "",
            //     "role": "system",
            //     "agent": 5
            // },
            // {
            //     "id": 12,
            //     "created": "2023-07-20T15:32:23.565939Z",
            //     "content": "[content]",
            //     "function_name": "ExtractSubTables",
            //     "role": "function",
            //     "agent": 5
            // },
            // {
            //     "id": 13,
            //     "created": "2023-07-20T15:32:23.568798Z",
            //     "content": "different content",
            //     "function_name": "",
            //     "role": "assistant",
            //     "agent": 5
            // },
        //     ],
        //     "created": "2023-07-20T15:32:23.416860Z",
        //     "completed": null,
        //     "dataset": 8,
        //     "task": 6
        // }
        // Or possibly results might be 404 and None, in which case  display a message saying "Thanks for publishing your data. <input type="button">Publish another dataset</input>" - Clicking on the button should just refresh the page
          // Hide initial-message div
          // startChat(results["message_set"], results["id"]);
        })
      }
    })
  }

  // Run an interactive conversation
  function startChat(messages, agent_id) {
    // Show the chats div
    // Create a child 'chat' class div like the one below, and populate it with messages
    // Each message should have an additional 'assistant' or 'user' class, don't display the 'system' messages or 'function' messages
    /*
    <div class="chat in-progress">
      <div class="messages">
        {messages.map((message, index) => (
          <div key={index} className='flex flex-col message'}><p>{message}</p></div>
        ))}
      </div>

      <input type="text" />
    </div>*/
    // This is basically a chat interface split into chunks, each chunk dealing with a particular Agent/task.
    // When the user writes text in the input and then presses enter, the following should happen:
    // display the user's message in the messages div
    // show a simple animation of three dots ... first 1 dot, then 2 dots, then 3 dots, repeating
    // disable the input box
    // make an object for the user's message: {'message': '[user message]' }
    // POST user's message object to 'http://publishgpt-back.local/agents/[agent_id]/chat'
    // Results will be a 200 OK new message object with role "assistant", or 404 NOT FOUND with no content
    // If it's 404 NOT FOUND, remove the 'in-progress' class and GET 'http://publishgpt-back.local/datasets/[dataset_id]/get_or_create_next_agent/' again as above, and start this whole process again
    // Otherwise, just stop the animation, display the assistant message, and enable the user input box again

  }


  return (
    <main className="flex flex-col items-center justify-between pb-40">
      <div className="border-gray-200sm:mx-0 mx-5 mt-5 max-w-screen-md rounded-md border sm:w-full">
        <div className="flex flex-col message bot initial-message">
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
          <div class="initial-errors"></div>
        </div>
        <div class="conversations">
        </div>
      </div>
    </main>
  );
}

// Note: OpenAPI yaml for the endpoints is available here http://publishgpt-back.local/api-schema/
export default IndexPage;
