import React from 'react';

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
    <div className="mt-4">
      {files.map((file, index) => (
        <div key={index} className="flex items-center justify-between py-2.5 px-3 bg-bg-secondary rounded-lg mb-1.5 animate-slide-in">
          <div className="flex items-center gap-2.5">
            <span className="text-accent-light">📄</span>
            <div>
              <div className="text-[0.85rem] font-medium">{file.name}</div>
              <div className="text-xs text-slate-500">{formatFileSize(file.size)}</div>
            </div>
          </div>
          <button
            type="button"
            className="bg-transparent border-none text-slate-500 cursor-pointer p-1 transition-colors hover:text-red-500"
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
