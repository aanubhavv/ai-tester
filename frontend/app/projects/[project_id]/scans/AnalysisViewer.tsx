import { useState } from "react";
import { Maximize2, Minimize2, CheckCircle2, AlertTriangle, XCircle, Info } from "lucide-react";

interface AnalysisViewerProps {
  analysis: any;
}

export default function AnalysisViewer({ analysis }: AnalysisViewerProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!analysis) return null;

  const renderSection = (title: string, data: any) => {
    if (!data) return null;

    if (Array.isArray(data)) {
      if (data.length === 0) return <p className="text-zinc-500 text-xs">None</p>;
      return (
        <ul className="list-disc pl-4 space-y-1 text-xs text-zinc-400">
          {data.map((item, i) => (
            <li key={i}>{typeof item === 'string' ? item : JSON.stringify(item)}</li>
          ))}
        </ul>
      );
    }

    if (typeof data === 'object') {
      return (
        <div className="flex flex-wrap gap-3">
          {Object.entries(data).map(([key, value]) => {
            if (key === 'h1' || key === 'h2' || key === 'h3' || key === 'errors' || key === 'warnings' || key === 'failed_requests') return null; // handled separately or skipped to avoid clutter
            return (
              <div key={key} className="bg-zinc-950 p-3 rounded-lg border border-zinc-800/80 flex flex-col justify-center min-w-[100px] flex-grow">
                <span className="block text-[10px] text-zinc-400 font-medium uppercase tracking-wider mb-1">{key.replace(/_/g, ' ')}</span>
                <span className={`font-semibold break-words block ${typeof value === 'number' ? 'text-lg text-blue-50' : 'text-sm text-zinc-200'}`} title={String(value)}>
                  {value !== null && value !== undefined ? String(value) : 'N/A'}
                </span>
              </div>
            );
          })}
        </div>
      );
    }

    return <span className="text-xs text-zinc-300">{String(data)}</span>;
  };

  const content = (
    <div className={`flex flex-col gap-6 ${isExpanded ? 'p-6 h-full' : ''}`}>
      {/* Metadata */}
      {analysis.metadata && (
        <section>
          <h4 className="font-semibold text-zinc-200 mb-2 border-b border-zinc-800 pb-1">Metadata</h4>
          {renderSection('Metadata', analysis.metadata)}
        </section>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Headings & DOM */}
        <div className="space-y-6">
          {analysis.headings && (
            <section>
              <h4 className="font-semibold text-zinc-200 mb-2 border-b border-zinc-800 pb-1">Headings</h4>
              {renderSection('Headings', analysis.headings)}
            </section>
          )}
          {analysis.dom && (
            <section>
              <h4 className="font-semibold text-zinc-200 mb-2 border-b border-zinc-800 pb-1">DOM Structure</h4>
              {renderSection('DOM', analysis.dom)}
            </section>
          )}
        </div>

        {/* Media & Links */}
        <div className="space-y-6">
          {analysis.images && (
            <section>
              <h4 className="font-semibold text-zinc-200 mb-2 border-b border-zinc-800 pb-1">Images</h4>
              {renderSection('Images', analysis.images)}
            </section>
          )}
          {analysis.links && (
            <section>
              <h4 className="font-semibold text-zinc-200 mb-2 border-b border-zinc-800 pb-1">Links</h4>
              {renderSection('Links', analysis.links)}
            </section>
          )}
        </div>
      </div>

      {/* Forms & Storage */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {analysis.forms && (
          <section>
            <h4 className="font-semibold text-zinc-200 mb-2 border-b border-zinc-800 pb-1">Forms</h4>
            {renderSection('Forms', analysis.forms)}
          </section>
        )}
        {analysis.storage && (
          <section>
            <h4 className="font-semibold text-zinc-200 mb-2 border-b border-zinc-800 pb-1">Browser Storage</h4>
            {renderSection('Storage', analysis.storage)}
          </section>
        )}
      </div>

      {/* Issues: Console & Network */}
      {(analysis.console || analysis.network) && (
        <section>
          <h4 className="font-semibold text-zinc-200 mb-2 border-b border-zinc-800 pb-1">Issues & Logs</h4>
          <div className="space-y-4">
            {analysis.console?.errors?.length > 0 && (
              <div>
                <span className="text-xs font-semibold text-red-400 flex items-center gap-1 mb-1"><XCircle className="w-3 h-3"/> Console Errors ({analysis.console.errors.length})</span>
                <div className="bg-zinc-950 border border-red-900/30 rounded p-2 max-h-32 overflow-y-auto">
                  {analysis.console.errors.map((err: any, i: number) => (
                    <div key={i} className="text-xs text-red-300/80 mb-1 font-mono break-all">{err.text}</div>
                  ))}
                </div>
              </div>
            )}
            {analysis.console?.warnings?.length > 0 && (
              <div>
                <span className="text-xs font-semibold text-amber-400 flex items-center gap-1 mb-1"><AlertTriangle className="w-3 h-3"/> Console Warnings ({analysis.console.warnings.length})</span>
                <div className="bg-zinc-950 border border-amber-900/30 rounded p-2 max-h-32 overflow-y-auto">
                  {analysis.console.warnings.map((warn: any, i: number) => (
                    <div key={i} className="text-xs text-amber-300/80 mb-1 font-mono break-all">{warn.text}</div>
                  ))}
                </div>
              </div>
            )}
            {analysis.network?.failed_requests?.length > 0 && (
              <div>
                <span className="text-xs font-semibold text-red-400 flex items-center gap-1 mb-1"><XCircle className="w-3 h-3"/> Network Failures ({analysis.network.failed_requests.length})</span>
                <div className="bg-zinc-950 border border-red-900/30 rounded p-2 space-y-2">
                  {analysis.network.failed_requests.map((req: any, i: number) => (
                    <div key={i} className="text-xs pb-2 border-b border-red-900/20 last:border-0 last:pb-0 font-mono break-all">
                      <div className="font-semibold text-red-400">{req.method} <span className="text-red-300/80">({req.failure_reason})</span></div>
                      <div className="text-red-300/60 mt-0.5">{req.url}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {!(analysis.console?.errors?.length > 0) && !(analysis.console?.warnings?.length > 0) && !(analysis.network?.failed_requests?.length > 0) && (
              <span className="text-xs text-zinc-500 flex items-center gap-1"><CheckCircle2 className="w-3 h-3 text-emerald-500"/> No significant issues detected</span>
            )}
          </div>
        </section>
      )}
    </div>
  );

  return (
    <>
      <div className="bg-zinc-900 p-4 rounded-lg border border-zinc-800 flex flex-col relative h-full">
        <div className="flex items-center justify-between mb-4 shrink-0">
          <span className="block font-medium text-zinc-300 flex items-center gap-2">
            <Info className="h-4 w-4 text-blue-400" /> Analysis Data
          </span>
          <button 
            onClick={() => setIsExpanded(true)}
            className="p-1.5 rounded-md hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            <Maximize2 className="h-4 w-4" />
          </button>
        </div>
        
        <div className="overflow-y-auto pr-2 flex-1 hide-scrollbar relative">
          {content}
        </div>
      </div>

      {isExpanded && (
        <div className="fixed inset-4 z-50 p-6 bg-zinc-950/95 backdrop-blur shadow-2xl rounded-xl border border-zinc-800 flex flex-col">
          <div className="flex items-center justify-between mb-6 shrink-0 border-b border-zinc-800 pb-4">
            <h3 className="text-xl font-bold text-zinc-100 flex items-center gap-2">
              <Info className="h-5 w-5 text-blue-400" /> Detailed Analysis
            </h3>
            <button 
              onClick={() => setIsExpanded(false)}
              className="p-2 rounded-md bg-zinc-800 hover:bg-zinc-700 text-zinc-200 transition-colors"
            >
              <Minimize2 className="h-5 w-5" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto pr-4 hide-scrollbar">
            <div className="max-w-4xl mx-auto w-full">
              {content}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
