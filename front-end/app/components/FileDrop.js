import React from 'react';
import { useDropzone } from 'react-dropzone';
import config from '../config.js';

const FileDrop = ({ onFileAccepted, onError, loading }) => {

  const onDrop = async (acceptedFiles) => {
    const formData = new FormData();
    formData.append('file', acceptedFiles[0]);

    try {
      const response = await fetch(`${config.baseApiUrl}/datasets/`, {
        method: 'POST',
        body: formData,
      });
      if (!response.ok) {
        let errorMessage = 'Upload failed';
    
        try {
          const errorData = await response.json();
    
          // Check for non-field errors first
          if (errorData.non_field_errors && errorData.non_field_errors.length > 0) {
            errorMessage = errorData.non_field_errors.join(' ');
          } else {
            // Iterate through all errors and concatenate messages
            const fieldErrors = Object.values(errorData).flat();
            if (fieldErrors.length > 0) {
              errorMessage = fieldErrors.join(' ');
            }
          }
        } catch (parseError) {
          // If response is not JSON, use the status text
          errorMessage = response.statusText || errorMessage;
        }
    
        // Throw an error with the detailed message
        throw new Error(errorMessage);
      }
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
