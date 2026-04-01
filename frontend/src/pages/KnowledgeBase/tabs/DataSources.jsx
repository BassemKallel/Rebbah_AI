import React, { useState } from 'react';
import { UploadCloud, FileText, CheckCircle, Clock } from 'lucide-react';

const mockFiles = [
  { id: 1, name: 'Return_Policy.pdf', size: '124 KB', status: 'parsed', date: '2 hours ago' },
  { id: 2, name: 'Size_Guide_SS24.pdf', size: '2.4 MB', status: 'parsed', date: 'Yesterday' },
  { id: 3, name: 'Shipping_Rates.csv', size: '14 KB', status: 'processing', date: 'Just now' },
];

const DataSources = () => {
  const [isDragging, setIsDragging] = useState(false);

  return (
    <div className="max-w-4xl">
      <h1 className="text-[22px] font-extrabold text-gray-800 mb-1">Data Sources</h1>
      <p className="text-[15px] font-medium text-gray-400 mb-8">Upload documents to expand your AI agent's knowledge. Supported formats: .pdf, .docx, .txt, .csv</p>
      
      {/* Upload Zone */}
      <div 
        className={`border-2 border-dashed rounded-3xl p-12 flex flex-col items-center justify-center text-center transition-all duration-200 mb-8 cursor-pointer
          ${isDragging ? 'border-[#0f6885] bg-[#0f6885]/5 shadow-sm scale-[1.01]' : 'border-gray-200 bg-white hover:border-[#0f6885]/50 hover:bg-gray-50'}`}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => { e.preventDefault(); setIsDragging(false); }}
      >
        <div className="w-16 h-16 bg-[#eef6f9] text-[#0f6885] rounded-full flex items-center justify-center mb-5 shadow-sm">
           <UploadCloud className="w-8 h-8" />
        </div>
        <h3 className="text-[17px] font-bold text-gray-800 mb-2">Click or drag files to upload</h3>
        <p className="text-[14px] text-gray-400 font-medium max-w-sm">
          Maximum file size is 50MB. Text is extracted automatically to train your agent.
        </p>
      </div>

      {/* Uploaded Files Table */}
      <div className="mb-4">
        <h3 className="text-[15px] font-bold text-gray-800 mb-4">Trained Documents ({mockFiles.length})</h3>
        
        <div className="flex flex-col gap-3">
           {mockFiles.map(file => (
             <div key={file.id} className="bg-white border border-gray-100 rounded-2xl p-4 flex items-center justify-between shadow-sm hover:border-[#0f6885]/30 transition-colors">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-gray-50 rounded-xl flex items-center justify-center text-gray-400 border border-gray-100">
                     <FileText className="w-6 h-6" />
                  </div>
                  <div>
                    <h4 className="text-[15px] font-semibold text-gray-800">{file.name}</h4>
                    <span className="text-[13px] text-gray-400 font-medium">{file.size} • Uploaded {file.date}</span>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                   {file.status === 'parsed' ? (
                     <div className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 text-emerald-600 rounded-lg border border-emerald-100/50">
                        <CheckCircle className="w-4 h-4" />
                        <span className="text-[12px] font-bold uppercase tracking-wider">Active</span>
                     </div>
                   ) : (
                     <div className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-50 text-amber-600 rounded-lg border border-amber-100/50">
                       <Clock className="w-4 h-4 animate-pulse" />
                       <span className="text-[12px] font-bold uppercase tracking-wider">Processing</span>
                     </div>
                   )}
                </div>
             </div>
           ))}
        </div>
      </div>
    </div>
  );
};

export default DataSources;
