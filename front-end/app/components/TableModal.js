import React, { useState, useEffect } from 'react';
import Modal from 'react-bootstrap/Modal';
import DataTable from 'react-data-table-component';
import Button from 'react-bootstrap/Button';

const TableModal = ({ showTable, handleCloseTable, table_id }) => {
    const [tableData, setTableData] = useState([]);
    const [tableColumns, setTableColumns] = useState([]);

    useEffect(() => {
        if(table_id) { fetchTableData(table_id); }
    }, [table_id]);

    const fetchTableData = (table_id) => {
        fetch(`http://localhost:8000/api/tables/${table_id}`)
        .then(response => response.json())
        .then(df => { 
            const df_json = JSON.parse(df.df_json);
            const columns = Object.keys(df_json[0]).map((column) => ({
                name: column,
                selector: row => row[column],
            }));
            setTableColumns(columns);
            setTableData(df_json);
        });
    };

    return (
        <Modal show={showTable} onHide={handleCloseTable} size="lg">
            <Modal.Header closeButton>
                <Modal.Title>Modal heading</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <DataTable columns={tableColumns} data={tableData} pagination dense />
            </Modal.Body>
            <Modal.Footer>
                <Button variant="secondary" onClick={handleCloseTable}>
                    Close
                </Button>
                <Button variant="primary" onClick={handleCloseTable}>
                    Save Changes
                </Button>
            </Modal.Footer>
        </Modal>
    );
}

export default TableModal;
