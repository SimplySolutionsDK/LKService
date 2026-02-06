import { useState } from 'react';
import { Header } from './components/layout/Header';
import { Footer } from './components/layout/Footer';
import { UploadCard } from './components/upload/UploadCard';
import { SettingsCard } from './components/upload/SettingsCard';
import { ApiFetchCard } from './components/api-fetch/ApiFetchCard';
import { PreviewSection } from './components/preview/PreviewSection';
import { EntriesModal } from './components/modals/EntriesModal';
import { useFileUpload } from './hooks/useFileUpload';
import { usePreview } from './hooks/usePreview';
import type { EmployeeType, DailyRecord, ApiFetchParams } from './types';
import './App.css';

function App() {
  const { files, addFiles, removeFile } = useFileUpload();
  const [employeeType, setEmployeeType] = useState<EmployeeType>('Svend');
  const [selectedRecord, setSelectedRecord] = useState<DailyRecord | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const {
    previewData,
    activeTab,
    outputFormat,
    callOutSelections,
    absenceSelections,
    status,
    isLoading,
    setActiveTab,
    setOutputFormat,
    loadPreview,
    loadPreviewFromApi,
    exportData,
    updateCallOutSelection,
    updateAbsenceSelection,
    clearPreview,
  } = usePreview();

  const handleFilesSelected = (newFiles: File[]) => {
    addFiles(newFiles);
    clearPreview();
  };

  const handleFileRemove = (index: number) => {
    removeFile(index);
    clearPreview();
  };

  const handlePreview = async () => {
    if (files.length === 0) return;
    await loadPreview(files, employeeType);
  };

  const handleApiFetchedData = async (params: ApiFetchParams) => {
    // Clear any uploaded CSV files when using API fetch
    if (files.length > 0) {
      files.forEach((_, index) => removeFile(index));
    }
    await loadPreviewFromApi(params, employeeType);
  };

  const handleShowDetails = (index: number) => {
    if (previewData?.daily[index]) {
      setSelectedRecord(previewData.daily[index]);
      setIsModalOpen(true);
    }
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedRecord(null);
  };

  return (
    <div className="container">
      <Header />

      <div className="upload-section">
        <form onSubmit={(e) => { e.preventDefault(); handlePreview(); }}>
          <div className="upload-controls">
            <UploadCard
              files={files}
              onFilesSelected={handleFilesSelected}
              onFileRemove={handleFileRemove}
            />

            <SettingsCard
              employeeType={employeeType}
              onEmployeeTypeChange={setEmployeeType}
              onPreview={handlePreview}
              previewDisabled={files.length === 0 || isLoading}
              status={status}
            />
          </div>

          <div className="api-fetch-section">
            <ApiFetchCard
              onDataFetched={handleApiFetchedData}
              employeeType={employeeType}
              isLoading={isLoading}
            />
          </div>

          <div className="info-box">
            <strong>Overtidsberegning (DBR/Industriens Overenskomst 2026):</strong><br />
            • Normtid: 37 timer ugentligt<br />
            • Hverdage: Timer-tærskel (1./2., 3./4., 5.+ time) + tid-på-dagen (06-18 / 18-06)<br />
            • Lørdag: Anvendes fridag-satser (dag: 76,80 kr, nat: 143,70 kr)<br />
            • Søndag: Før kl. 12 (95,75 kr), efter kl. 12 (143,70 kr)<br />
            • Call-out: 750 kr ved arbejde før 07:00 eller fra 15:30<br />
            <small>Satser gældende fra 1. marts 2026</small>
          </div>
        </form>

        {previewData && (
          <PreviewSection
            data={previewData}
            activeTab={activeTab}
            outputFormat={outputFormat}
            callOutSelections={callOutSelections}
            absenceSelections={absenceSelections}
            onTabChange={setActiveTab}
            onFormatChange={setOutputFormat}
            onCallOutChange={updateCallOutSelection}
            onAbsenceChange={updateAbsenceSelection}
            onShowDetails={handleShowDetails}
            onExport={exportData}
          />
        )}
      </div>

      <EntriesModal
        isOpen={isModalOpen}
        record={selectedRecord}
        onClose={handleCloseModal}
      />

      <Footer />
    </div>
  );
}

export default App;
