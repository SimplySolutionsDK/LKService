import React from 'react';
import { Card, CardTitle } from '../ui/Card';
import { Dropzone } from './Dropzone';
import { FileList } from './FileList';

interface UploadCardProps {
  files: File[];
  onFilesSelected: (files: File[]) => void;
  onFileRemove: (index: number) => void;
}

export const UploadCard: React.FC<UploadCardProps> = ({
  files,
  onFilesSelected,
  onFileRemove,
}) => {
  return (
    <Card>
      <CardTitle icon="📁">Upload CSV Filer</CardTitle>
      <Dropzone onFilesSelected={onFilesSelected} />
      <FileList files={files} onRemove={onFileRemove} />
    </Card>
  );
};
