import React, { useRef, useState } from 'react';
import clsx from 'clsx';

interface DropzoneProps {
  onFilesSelected: (files: File[]) => void;
}

export const Dropzone: React.FC<DropzoneProps> = ({ onFilesSelected }) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const files = Array.from(e.dataTransfer.files).filter(f => f.name.endsWith('.csv'));
    if (files.length > 0) {
      onFilesSelected(files);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      onFilesSelected(files);
    }
  };

  return (
    <>
      <div
        className={clsx(
          'border-2 border-dashed rounded-xl py-8 px-6 text-center cursor-pointer transition-all max-md:py-6 max-md:px-4',
          isDragOver
            ? 'border-accent bg-blue-500/[0.08]'
            : 'border-border bg-blue-500/[0.02] hover:border-accent hover:bg-blue-500/[0.08]'
        )}
        onClick={handleClick}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <div className="text-[2.5rem] mb-3 opacity-70 max-md:text-[2rem]">📄</div>
        <p className="text-slate-400 text-[0.9rem] max-md:text-[0.85rem]">
          <strong className="text-accent-light">Klik for at vælge filer</strong><br />
          eller træk og slip CSV-filer her
        </p>
      </div>
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        multiple
        accept=".csv"
        onChange={handleFileChange}
      />
    </>
  );
};
