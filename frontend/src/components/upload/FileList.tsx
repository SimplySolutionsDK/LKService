import React from 'react';
import './FileList.css';

interface FileListProps {
  files: File[];
  onRemove: (index: number) => void;
}

const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
};

export const FileList: React.FC<FileListProps> = ({ files, onRemove }) => {
  if (files.length === 0) return null;

  return (
    <div className="file-list">
      {files.map((file, index) => (
        <div key={index} className="file-item">
          <div className="file-item-info">
            <span className="file-icon">📄</span>
            <div>
              <div className="file-name">{file.name}</div>
              <div className="file-size">{formatFileSize(file.size)}</div>
            </div>
          </div>
          <button
            type="button"
            className="remove-file"
            onClick={() => onRemove(index)}
            aria-label="Remove file"
          >
            ✕
          </button>
        </div>
      ))}
    </div>
  );
};
