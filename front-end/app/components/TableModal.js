import React, { useState, useEffect } from 'react';
import Modal from 'react-bootstrap/Modal';
import DataTable from 'react-data-table-component';
import Button from 'react-bootstrap/Button';
import config from '../config.js';

const TableModal = ({ showTable, handleCloseTable, table_id }) => {
    const [tableData, setTableData] = useState([]);
    const [tableColumns, setTableColumns] = useState([]);

    useEffect(() => {
        if(table_id) { fetchTableData(table_id); }
    }, [table_id]);

    const fetchTableData = (table_id) => {
        fetch(`${config.baseApiUrl}/pi/tables/${table_id}`)
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
        <Modal show={showTable} onHide={(event) => handleCloseTable(event)} size="lg">
            <Modal.Header>
                <Modal.Title>Table {table_id}</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <DataTable columns={tableColumns} data={tableData} pagination dense />
            </Modal.Body>
            <Modal.Footer>
                <Button onClick={(event) => handleCloseTable(event)}>Close</Button>
            </Modal.Footer>
        </Modal>
    );
}

export default TableModal;
