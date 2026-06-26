import { useState, useRef, FormEvent, ChangeEvent, DragEvent } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Upload, FileText, Play, ChevronDown, Check, AlertTriangle } from 'lucide-react';
import AppLayout from '../components/AppLayout';

export default function UploadPage() {
  const [searchParams] = useSearchParams();
  const sessionId = searchParams.get('session');
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState<'paste' | 'upload'>('paste');
  const [rawText, setRawText] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [column, setColumn] = useState('review');
  const [detectedColumns] = useState(['review', 'feedback', 'comment', 'text', 'message']);
  const [loading, setLoading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) handleFileSelect(droppedFile);
  };

  const handleFileSelect = (selectedFile: File) => {
    setFile(selectedFile);
    setColumn('review');
  };

  const handleFileInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) handleFileSelect(selectedFile);
  };

  const handleSubmitPaste = async (e: FormEvent) => {
    e.preventDefault();
    if (!rawText.trim()) return;
    setLoading(true);
    await new Promise((resolve) => setTimeout(resolve, 1000));
    navigate(`/analyse/processing?session=${sessionId || 'mock_session'}`);
  };

  const handleSubmitFile = async (e: FormEvent) => {
    e.preventDefault();
    if (!file || !column) return;
    setLoading(true);
    await new Promise((resolve) => setTimeout(resolve, 1000));
    navigate(`/analyse/processing?session=${sessionId || 'mock_session'}`);
  };

  return (
    <AppLayout>
      <div className="max-w-3xl mx-auto">
        {/* Preview Banner */}
        <div className="mb-6 bg-gradient-to-r from-yellow-50 to-amber-50 border border-yellow-200 rounded-2xl px-5 py-3.5 flex items-center gap-3 shadow-sm">
          <div className="w-10 h-10 rounded-xl bg-yellow-100 flex items-center justify-center flex-shrink-0">
            <AlertTriangle className="w-5 h-5 text-yellow-600" />
          </div>
          <p className="text-yellow-800 text-sm">
            <span className="font-semibold">Preview mode</span> — no backend connected. Uploads will be simulated.
          </p>
        </div>

        <div className="mb-8 flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl gradient-bg flex items-center justify-center shadow-lg">
            <Upload className="w-7 h-7 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Upload Your Reviews</h1>
            <p className="text-muted">Paste text or upload a file to begin analysis</p>
          </div>
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-3xl border border-gray-100 shadow-xl overflow-hidden">
          <div className="flex border-b border-gray-100">
            <button
              onClick={() => setActiveTab('paste')}
              className={`flex-1 flex items-center justify-center gap-2 px-6 py-4 text-sm font-medium border-b-2 transition-all ${
                activeTab === 'paste'
                  ? 'border-primary bg-primary/5 text-primary'
                  : 'border-transparent text-muted hover:text-gray-700'
              }`}
            >
              <FileText className="w-4 h-4" />
              Paste Text
            </button>
            <button
              onClick={() => setActiveTab('upload')}
              className={`flex-1 flex items-center justify-center gap-2 px-6 py-4 text-sm font-medium border-b-2 transition-all ${
                activeTab === 'upload'
                  ? 'border-primary bg-primary/5 text-primary'
                  : 'border-transparent text-muted hover:text-gray-700'
              }`}
            >
              <Upload className="w-4 h-4" />
              Upload File
            </button>
          </div>

          <div className="p-6">
            {activeTab === 'paste' && (
              <form onSubmit={handleSubmitPaste}>
                <label className="block text-sm font-medium text-gray-700 mb-2">Enter your reviews</label>
                <p className="text-muted text-xs mb-4">One review per line or separated by double newline.</p>
                <textarea
                  value={rawText}
                  onChange={(e) => setRawText(e.target.value)}
                  rows={10}
                  className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 text-gray-800 focus:outline-none focus:border-primary focus:ring-4 focus:ring-primary/10 resize-none font-mono text-sm transition-all"
                  placeholder={`Great product, fast shipping!\n\nThe customer service was helpful but the product arrived late.\n\nLove the new update, much faster now!`}
                />
                <div className="mt-6 flex justify-end">
                  <button
                    type="submit"
                    disabled={!rawText.trim() || loading}
                    className="flex items-center gap-2 gradient-bg text-white font-semibold rounded-xl px-6 py-3.5 shadow-lg hover:shadow-xl transition-all hover:scale-[1.02] disabled:opacity-50"
                  >
                    <Play className="w-4 h-4" />
                    {loading ? 'Processing...' : 'Run Analysis'}
                  </button>
                </div>
              </form>
            )}

            {activeTab === 'upload' && (
              <form onSubmit={handleSubmitFile}>
                <div
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className={`border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all ${
                    dragOver
                      ? 'border-primary bg-primary/5'
                      : 'border-gray-200 hover:border-primary hover:bg-gray-50'
                  }`}
                >
                  <div className={`w-16 h-16 mx-auto rounded-2xl flex items-center justify-center mb-4 transition-all ${
                    dragOver ? 'gradient-bg shadow-lg' : 'bg-gray-100'
                  }`}>
                    <Upload className={`w-8 h-8 ${dragOver ? 'text-white' : 'text-muted'}`} />
                  </div>
                  <p className="text-gray-700 font-medium mb-1">
                    {file ? file.name : 'Drop a CSV or Excel file here'}
                  </p>
                  <p className="text-muted text-sm">
                    {file ? (
                      <span className="flex items-center justify-center gap-2 text-green-500">
                        <Check className="w-4 h-4" />
                        Click to change file
                      </span>
                    ) : (
                      'or click to browse'
                    )}
                  </p>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".csv,.xlsx,.xls"
                    onChange={handleFileInputChange}
                    className="hidden"
                  />
                </div>

                {file && (
                  <div className="mt-6 bg-gray-50 rounded-xl p-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">Review column</label>
                    <div className="relative">
                      <select
                        value={column}
                        onChange={(e) => setColumn(e.target.value)}
                        className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 text-gray-800 focus:outline-none focus:border-primary focus:ring-4 focus:ring-primary/10 bg-white appearance-none pr-10 transition-all"
                      >
                        {detectedColumns.map((col) => (
                          <option key={col} value={col}>{col}</option>
                        ))}
                      </select>
                      <ChevronDown className="w-4 h-4 absolute right-4 top-1/2 -translate-y-1/2 text-muted pointer-events-none" />
                    </div>
                    <p className="text-xs text-muted mt-2">Select the column containing your customer reviews</p>
                  </div>
                )}

                <div className="mt-6 flex justify-end">
                  <button
                    type="submit"
                    disabled={!file || !column || loading}
                    className="flex items-center gap-2 gradient-bg text-white font-semibold rounded-xl px-6 py-3.5 shadow-lg hover:shadow-xl transition-all hover:scale-[1.02] disabled:opacity-50"
                  >
                    <Play className="w-4 h-4" />
                    {loading ? 'Processing...' : 'Run Analysis'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
