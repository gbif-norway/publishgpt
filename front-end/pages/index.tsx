import { useState, useEffect } from 'react';

const IndexPage = () => {
  const [conversation, setConversation] = useState([]);
  const [userInput, setUserInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [datasetSample, setDatasetSample] = useState('');

  const onFileDrop = async (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setLoading(true);

    const formData = new FormData();
    formData.append('file', e.dataTransfer.files[0]);
    try {
      const response = await fetch("http://publishgpt-back.local/datasets/", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        setErrorMessage(errorData.message);
      } else {
        const data = await response.json();
        setDatasetSample(data['df_sample']);
        const agentResponse = await fetch(`http://publishgpt-back.local/datasets/${data['id']}/get_or_create_next_agent/`);
        if (agentResponse.ok) {
          const agentData = await agentResponse.json();
          startChat(agentData["message_set"], agentData["id"]);
        } else {
          setErrorMessage("Thanks for publishing your data.");
          setLoading(false);
        }
      }
    } catch (error) {
      setErrorMessage(error.message);
    }
  };

  const startChat = (messages, agent_id) => {
    setConversation(messages.filter(message => message.role !== "system" && message.role !== "function"));
  };

  const sendMessage = async (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      const newMessage = { 'message': userInput };
      setConversation([...conversation, newMessage]);
      setUserInput('');
      setLoading(true);

      try {
        const response = await fetch(`http://publishgpt-back.local/agents/${agent_id}/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(newMessage),
        });

        if (response.ok) {
          const responseData = await response.json();
          setConversation([...conversation, responseData]);
        } else {
          setErrorMessage('An error occurred. Please try again.');
        }
      } catch (error) {
        setErrorMessage(error.message);
      } finally {
        setLoading(false);
      }
    }
  };

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
          {errorMessage && <div class="initial-errors">{errorMessage}</div>}
        </div>
        <div class="conversations">
          {conversation.map((message, index) => (
            <div key={index} className={`flex flex-col message ${message.role}`}>
              <p>{message.content}</p>
            </div>
          ))}
          <input type="text" value={userInput} onChange={e => setUserInput(e.target.value)} onKeyPress={sendMessage} disabled={loading} />
        </div>
      </div>
    </main>
  );
}

export default IndexPage;
