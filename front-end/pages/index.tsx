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
          // GET 'http://publishgpt-back.local/datasets/' + data['pk'] + '/next_conversation_task/'
          // OpenAPI yaml available here http://publishgpt-back.local/api-schema/
          // Results will look like this:
          // conversation = {
          //   "id": 1,
          //   "created": "2023-07-10",
          //   "updated_df_sample": "{\"date\":{\"1\":\"01\\/03\\/2012\",\"2\":\"02\\/03\\/2012\",\"3\":\"03\\/03\\/2012\"},\"genus\":{\"1\":\"Eudyptes\",\"2\":\"Eudyptes\",\"3\":\"Eudyptes\"},\"specific epithet\":{\"1\":\"moseleyi\",\"2\":\"moseleyi\",\"3\":\"moseleyi\"},\"count\":{\"1\":\"5\",\"2\":\"10\",\"3\":\"10\"},\"location\":{\"1\":\"Gough Island\",\"2\":\"Gough Island\",\"3\":\"Gough Island\"}}",
          //   "status": "in-progress",
          //   "dataset": 1, // data['pk']
          //   "task": 1
          //   "message_set": [{"role": "system", "content": "x"}, {"role": "assistant", "content": "y", "df_sample": "[some pandas dataframe]"}]
          // }
          // Hide initial-message div
          // startConversation(conversation);
        })
      }
    })
  }

  // Run an interactive conversation
  function startConversation(conversation) {
    // Show the conversations div
    // Create a child 'conversation' class div like the one below, and populate it with messages
    // Each message should have an additional 'assistant' or 'user' class, don't display the "system" messages
    /*
    <div class="conversation in-progress">
      <div class="messages">
        {conversation.map((message, index) => (
          <div key={index} className='flex flex-col message'}><p>{message}</p></div>
        ))}
      </div>

      <input type="text" />
    </div>*/
    // This is basically a chat interface split into chunks, each chunk dealing with a particular task.
    // When the user writes text in the input and then presses enter, the following should happen:
    // display the user's message in the messages div
    // show a simple animation of three dots ... first 1 dot, then 2 dots, then 3 dots, repeating
    // disable the input box
    // make an object for the user's message, something like {'role': 'user', 'content': '[user message]', 'conversation_id': conversation['id']}
    // POST user's message object to 'http://publishgpt-back.local/messages/post_message_and_get_reply/'
    // Results will be an array of message objects, including the user's message and with a reply at the end of it, the reply will be something like like {"role": "assistant", "content": "y", "df_sample": "[some pandas dataframe]", "conversation_id": x}
    // If the conversation ID has changed, remove the "in-progress" class of the conversation div and its input field, and create a new conversation div displaying the new set of messages 
    // If the conversation ID has not changed, just display the new message with the 'assistant' class, and display the df_sample content underneath, no processing necessary as it will be in html table format
    // df_sample may also be null, in which case just the message is displayed
    // enable the input box again
    // Repeat for the next message
    // If next message returns None........
    // If the conversation is complete GET 'http://publishgpt-back.local/datasets/' + data['pk'] + '/next_conversation_task/' and repeat the process
    // If GET 'http://publishgpt-back.local/datasets/' + data['pk'] + '/next_conversation_task/' returns None, then display a message saying "Thanks for publishing your data. <input type="button">Publish another dataset</input>"
    // Clicking on the button should just refresh the page
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

export default IndexPage;
