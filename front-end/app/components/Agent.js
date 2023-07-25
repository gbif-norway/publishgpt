import Message from './Message';
import { useState, useEffect, useRef } from 'react';
import Accordion from 'react-bootstrap/Accordion';
import Button from 'react-bootstrap/Button';
import Badge from 'react-bootstrap/Badge';
import Modal from 'react-bootstrap/Modal';
import {
  DatatableWrapper,
  Filter,
  Pagination,
  PaginationOpts,
  TableBody,
  TableHeader
} from 'react-bs-datatable';
import { Col, Row, Table } from 'react-bootstrap';

const Agent = ({ agent, refreshAgents }) => {
    const [messages, setMessages] = useState(agent.message_set);
    const [isComplete, setIsComplete] = useState(agent.completed !== null);
    const [userInput, setUserInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [loadingMessage, setLoadingMessage] = useState("Working...");
    const [showDataset, setShowDataset] = useState(false);

    const updateMessages = (newData) => {
      const newMessages = [...messages, ...newData];
      const uniqueMessagesMap = new Map(newMessages.map(msg => [msg.id, msg]));
      const uniqueSortedMessages = Array.from(uniqueMessagesMap.values())
          .sort((a, b) => a.id - b.id);
      setMessages(uniqueSortedMessages);
    };

    const handleUserInput = (event) => {
      if (event.key === 'Enter') {
        event.preventDefault();
        
        setIsLoading(true);
        setLoadingMessage("Working...");

        // after 10 seconds, change the loading message
        const timeoutId = setTimeout(() => {
            setLoadingMessage("Still working...");
        }, 10000);

        // Set an interval to fetch messages every 5 seconds
        const intervalId = setInterval(() => {
          fetch(`http://localhost:8000/api/agents/${agent.id}/`)
            .then(response => response.json())
            .then(data => {
              updateMessages(data.message_set);
            })
            .catch((error) => {
                console.error("Error:", error);
            });
        }, 5000);
        
        fetch(`http://localhost:8000/api/messages/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: userInput, display_to_user: true, role: 'user', agent: agent.id })
        })
        .then(response => response.json())
        .then(data => {
            updateMessages([data]);
            fetch(`http://localhost:8000/api/agents/${agent.id}/next_agent_message`)
            .then(response => response.json())
            .then(data => {
              if (data.id) {
                updateMessages([data]);
              } else {
                setIsComplete(true);
                refreshAgents();
              }
              setIsLoading(false);  // stop loading
              clearTimeout(timeoutId);  // clear the timeout
              clearInterval(intervalId);  // clear the interval
            })
        })
        .catch((error) => {
            console.error("Error:", error);
            setIsLoading(false);  // stop loading in case of error
            clearTimeout(timeoutId);  // clear the timeout
            clearInterval(intervalId);  // clear the interval
        });

        setUserInput("");
      }
    };

    function handleShowDataset(agent_id) {
      setShowDataset(true);
    };

    const handleCloseDataset = () => setShowDataset(false);

    if (messages.filter(function(message) { return (message.display_to_user) }).length === 0 && isComplete) {
      return null; // return null to not render anything
    };

    // Create table headers consisting of 4 columns.
    const headers = [
      { title: 'Username', prop: 'username' },
      { title: 'Name', prop: 'realname' },
      { title: 'Location', prop: 'location' }
    ];

    // Randomize data of the table columns.
    // Note that the fields are all using the `prop` field of the headers.
    const body = [{
      username: 'i-am-billy',
      realname: `Billy 34`,
      location: 'Mars'
    }, {
    username: 'john-nhoj',
    realname: `John 23`,
    location: 'Saturn'
  }];


    return (
      <>
        <Accordion.Item eventKey={agent.id}>
          <Accordion.Header>
            Task: {agent.id} {agent.task.name.replace(/^[-_]*(.)/, (_, c) => c.toUpperCase()).replace(/[-_]+(.)/g, (_, c) => ' ' + c.toUpperCase())}
            {isComplete && (
            <span>&nbsp;<Badge bg="secondary">complete <i className="bi-check-square"></i></Badge></span>
            )}
          </Accordion.Header>
          <Accordion.Body>
          <div className="dataset-info-wrapper">
            Working with&nbsp;
            <Button variant="info" size="sm" onClick={() => handleShowDataset(agent.id)}><i className="bi-table"></i>&nbsp;Dataframe ID 234 (Species)</Button>{' '}
            <Button variant="info" size="sm"><i className="bi-table"></i>&nbsp;Dataframe ID 1423 (Variables)</Button>{' '}
          </div>

          {messages.filter(function(message) { return (message.display_to_user) }).map((message, i) => (
            <Message key={i} role={message.role} content={message.content} />
          ))}

          {isLoading && (
            <div className="message assistant-message">
              <div className="d-flex align-items-center">
                <strong>{loadingMessage}</strong>
                <div className="spinner-border ms-auto" role="status" aria-hidden="true"></div>
              </div>
            </div>
          )}
          {!isComplete && !isLoading && <input type="text" className="form-control user-input" value={userInput} onKeyPress={handleUserInput} onChange={e => setUserInput(e.target.value)} />}
          </Accordion.Body>
        </Accordion.Item>
        
        <Modal show={showDataset} onHide={handleCloseDataset}>
          <Modal.Header closeButton>
            <Modal.Title>Modal heading</Modal.Title>
          </Modal.Header>
          <Modal.Body>

          <DatatableWrapper body={body} headers={headers}>
            <Row className="mb-4">
              <Col
                xs={12}
                lg={4}
                className="d-flex flex-col justify-content-end align-items-end"
              >
                <Filter />
              </Col>
              <Col
                xs={12}
                sm={6}
                lg={4}
                className="d-flex flex-col justify-content-lg-center align-items-center justify-content-sm-start mb-2 mb-sm-0"
              >
                <PaginationOpts />
              </Col>
              <Col
                xs={12}
                sm={6}
                lg={4}
                className="d-flex flex-col justify-content-end align-items-end"
              >
                <Pagination />
              </Col>
            </Row>
            <Table>
              <TableHeader />
              <TableBody />
            </Table>
          </DatatableWrapper>

          </Modal.Body>
          <Modal.Footer>
            <Button variant="secondary" onClick={handleCloseDataset}>
              Close
            </Button>
            <Button variant="primary" onClick={handleCloseDataset}>
              Save Changes
            </Button>
          </Modal.Footer>
        </Modal>
      </>
    );
  };
  
export default Agent;
