import { useState } from 'react';
import Button from 'react-bootstrap/Button';
import TableModal from './TableModal';

function TableAssociations({ associations }) {
  const [showTable, setShowTable] = useState(false);
  const [tableId, setTableId] = useState(null);
  const handleShowTable = (event, table_id) => {
    event.stopPropagation(); 
    setTableId(table_id);
    setShowTable(true);
  };
  const handleCloseTable = (event) => {
    event && event.stopPropagation(); 
    setShowTable(false);
  }

  return (
    <>
    {associations.map(a => (
    <><Button variant="info" size="sm" key={a.table.id} onClick={(event) => handleShowTable(event, a.table.id)}>
        <i className="bi-table"></i>&nbsp;{a.table.title} ( Table ID {a.table.id} {a.operation})
    </Button>&nbsp;</>
    ))}
    {showTable && <TableModal showTable={showTable} table_id={tableId} handleCloseTable={handleCloseTable} />}
    </>
  );
}

export default TableAssociations;