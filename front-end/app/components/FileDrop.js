import React from 'react';
import { useDropzone } from 'react-dropzone';
import config from '../config.js';

const FileDrop = ({ onFileAccepted, onError }) => {
  const onDrop = async (acceptedFiles) => {
    const formData = new FormData();
    formData.append('file', acceptedFiles[0]);

    try {
      const response = await fetch(`${config.baseApiUrl}/datasets/`, {
        method: 'POST',
        body: formData,
      });
      if (!response.ok) throw new Error('Upload failed');
      const data = await response.json();
      onFileAccepted(data.id);
    } catch (err) {
      onError(err.message);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: false, // Ensure only one file is processed at a time
  });

  return (
    <div {...getRootProps()} className="file-drop">
      <input {...getInputProps()} />
      {isDragActive ? <p>Drop the file here ...</p> : <p>Drag and drop a file here, or click to select a file</p>}
    </div>
  );
};

export default FileDrop;
