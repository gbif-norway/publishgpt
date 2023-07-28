import { useState } from 'react';
import Button from 'react-bootstrap/Button';
import Collapse from 'react-bootstrap/Collapse';
import TableModal from './TableModal';

function FunctionMessage(message) {
  const [open, setOpen] = useState(false);
  const [showTable, setShowTable] = useState(false);
  const [tableId, setTableId] = useState(null);
  const handleShowTable = (table_id) => {
      setTableId(table_id);
      setShowTable(true);
  };
  const handleCloseTable = () => setShowTable(false);

  return (
    <>
    <div className={`message function-message`}>
        <Button onClick={() => setOpen(!open)} aria-controls={`collapseFor${message.id}`} aria-expanded={open}>Show work</Button>
        <Collapse in={open}><div id={`collapseFor${message.id}`}>{message.content}</div></Collapse>
        Resulting tables - updated, deleted, created:&nbsp;
        {message.tables.map(table => (
            <Button variant="info" size="sm" onClick={() => handleShowTable(table.id)}><i className="bi-table"></i>&nbsp;Table ID {table.id} ({table.sheet_name})</Button>
        ))}
    </div>
    {showTable && <TableModal showTable={showTable} table_id={tableId} handleCloseTable={handleCloseTable} />}
    </>
  );
}

export default FunctionMessage;