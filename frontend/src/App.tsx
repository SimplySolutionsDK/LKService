import { useState, useEffect } from 'react';
import clsx from 'clsx';
import { Header } from './components/layout/Header';
import { Footer } from './components/layout/Footer';
import { UploadCard } from './components/upload/UploadCard';
import { ApiFetchCard } from './components/api-fetch/ApiFetchCard';
import { PreviewSection } from './components/preview/PreviewSection';
import { EntriesModal } from './components/modals/EntriesModal';
import { DanlonConnection } from './components/danlon/DanlonConnection';
import { DanlonSync } from './components/danlon/DanlonSync';
import { Button } from './components/ui/Button';
import { Status } from './components/ui/Status';
import { useFileUpload } from './hooks/useFileUpload';
import { usePreview } from './hooks/usePreview';
import type { EmployeeType, DailyRecord, ApiFetchParams } from './types';

type DataSource = 'api' | 'csv';

const tabBase = 'flex-1 py-3 px-6 bg-transparent border-none rounded-lg text-[0.95rem] font-medium cursor-pointer transition-all flex items-center justify-center gap-2 max-md:w-full';

function App() {
  const { files, addFiles, removeFile } = useFileUpload();
  const [employeeType, setEmployeeType] = useState<EmployeeType>('Svend');
  const [selectedRecord, setSelectedRecord] = useState<DailyRecord | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [dataSource, setDataSource] = useState<DataSource>('api');
  const [danlonCompanyId, setDanlonCompanyId] = useState<string | undefined>();
  const [showDanlonSection, setShowDanlonSection] = useState(true);

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

  const handleSyncComplete = () => {
    // Optionally refresh or show a message
    console.log('Sync completed successfully');
  };

  // Check Danløn connection status on mount
  useEffect(() => {
    const checkDanlonConnection = async () => {
      try {
        const response = await fetch('/danlon/status');
        const data = await response.json();
        if (data.connected && data.company_id) {
          setDanlonCompanyId(data.company_id);
        }
      } catch (err) {
        console.error('Failed to check Danløn connection:', err);
      }
    };
    checkDanlonConnection();
  }, []);

  return (
    <div className="w-full max-w-[1400px] animate-fade-in">
      <Header 
        employeeType={employeeType}
        onEmployeeTypeChange={setEmployeeType}
      />

      <div className="flex flex-col gap-6">
        <div className="flex gap-3 mb-6 bg-bg-secondary p-2 rounded-xl border border-border max-md:flex-col max-md:gap-2">
          <button
            type="button"
            className={clsx(tabBase, dataSource === 'api'
              ? 'bg-accent text-white shadow-[0_4px_12px_var(--color-accent-glow)]'
              : 'text-slate-400 hover:bg-bg-card hover:text-slate-100'
            )}
            onClick={() => setDataSource('api')}
          >
            🔍 Hent fra API
          </button>
          <button
            type="button"
            className={clsx(tabBase, dataSource === 'csv'
              ? 'bg-accent text-white shadow-[0_4px_12px_var(--color-accent-glow)]'
              : 'text-slate-400 hover:bg-bg-card hover:text-slate-100'
            )}
            onClick={() => setDataSource('csv')}
          >
            📁 Upload CSV
          </button>
        </div>

        <form onSubmit={(e) => { e.preventDefault(); handlePreview(); }}>
          <div className="mb-6">
            {dataSource === 'api' ? (
              <ApiFetchCard
                onDataFetched={handleApiFetchedData}
                employeeType={employeeType}
                isLoading={isLoading}
              />
            ) : (
              <div className="flex flex-col gap-6">
                <UploadCard
                  files={files}
                  onFilesSelected={handleFilesSelected}
                  onFileRemove={handleFileRemove}
                />
                
                <div className="flex flex-col gap-4">
                  <Button
                    variant="primary"
                    onClick={handlePreview}
                    disabled={files.length === 0 || isLoading}
                  >
                    <span>👁</span>
                    Vis Preview
                  </Button>
                  {status && <Status type={status.type} message={status.message} />}
                </div>
              </div>
            )}
          </div>

          <div className="bg-blue-500/10 border border-blue-500/30 rounded-[10px] py-3.5 px-4 text-[0.8rem] text-slate-400 leading-relaxed mt-6">
            <strong className="text-accent-light">Overtidsberegning (DBR/Industriens Overenskomst 2026):</strong><br />
            • Normtid: 37 timer ugentligt<br />
            • Hverdage: Timer-tærskel (1./2., 3./4., 5.+ time) + tid-på-dagen (06-18 / 18-06)<br />
            • Lørdag: Anvendes fridag-satser (dag: 76,80 kr, nat: 143,70 kr)<br />
            • Søndag: Før kl. 12 (95,75 kr), efter kl. 12 (143,70 kr)<br />
            • Call-out: 750 kr ved arbejde før 07:00 eller fra 15:30<br />
            <small>Satser gældende fra 1. marts 2026</small>
          </div>
        </form>

        {/* Danløn Integration Section */}
        <div className="mt-6">
          <button
            type="button"
            className="flex items-center gap-2 text-lg font-semibold text-slate-200 hover:text-accent transition-colors mb-4"
            onClick={() => setShowDanlonSection(!showDanlonSection)}
          >
            <span className="text-2xl">{showDanlonSection ? '▼' : '▶'}</span>
            <span>🔗 Danløn Integration</span>
          </button>

          {showDanlonSection && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
              <DanlonConnection />
              {previewData && (
                <DanlonSync
                  companyId={danlonCompanyId}
                  hasData={!!previewData}
                  onSyncComplete={handleSyncComplete}
                />
              )}
            </div>
          )}
        </div>

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
