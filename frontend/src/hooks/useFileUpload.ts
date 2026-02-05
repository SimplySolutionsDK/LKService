import { useState, useCallback } from 'react';

export const useFileUpload = () => {
  const [files, setFiles] = useState<File[]>([]);

  const addFiles = useCallback((newFiles: File[]) => {
    setFiles(currentFiles => {
      const uniqueFiles = [...currentFiles];
      newFiles.forEach(file => {
        if (!uniqueFiles.some(f => f.name === file.name)) {
          uniqueFiles.push(file);
        }
      });
      return uniqueFiles;
    });
  }, []);

  const removeFile = useCallback((index: number) => {
    setFiles(currentFiles => currentFiles.filter((_, i) => i !== index));
  }, []);

  const clearFiles = useCallback(() => {
    setFiles([]);
  }, []);

  return {
    files,
    addFiles,
    removeFile,
    clearFiles,
  };
};
