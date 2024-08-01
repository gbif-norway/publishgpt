
import React, { useState } from 'react';
import { useDropzone } from 'react-dropzone';
import config from '../config.js';

const FileDrop = ({ onFileAccepted, onError }) => {
  const [loading, setLoading] = useState(false);

  const onDrop = async (acceptedFiles) => {
    const formData = new FormData();
    formData.append('file', acceptedFiles[0]);

    setLoading(true);

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
    } finally {
      setLoading(false);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: false, // Ensure only one file is processed at a time
  });

  return (
    <div {...getRootProps()} className="file-drop">
      <input {...getInputProps()} />
      {loading ? (
        <div className="spinner"></div>
      ) : isDragActive ? (
        <p>Drop the file here ...</p>
      ) : (
        <p>Drag and drop a file here, or click to select a file</p>
      )}
    </div>
  );
};

export default FileDrop;