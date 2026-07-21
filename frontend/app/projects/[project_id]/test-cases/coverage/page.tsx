"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";

export default function CoveragePage() {
  const { project_id } = useParams();
  const [coverage, setCoverage] = useState<any>(null);
  const [duplicates, setDuplicates] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, [project_id]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [covRes, dupesRes] = await Promise.all([
        fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/v1/projects/${project_id}/test-cases/coverage`),
        fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/v1/projects/${project_id}/test-cases/duplicates`)
      ]);
      
      if (covRes.ok) {
        setCoverage(await covRes.json());
      }
      if (dupesRes.ok) {
        const data = await dupesRes.json();
        setDuplicates(data.duplicates || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="animate-pulse">Loading coverage analysis...</div>;

  if (!coverage) {
    return <div className="p-4 bg-yellow-50 text-yellow-800 rounded">Run AI Planning and generate some test cases first.</div>;
  }

  const reqPercentage = coverage.total_requirements > 0 
    ? Math.round((coverage.covered_requirements / coverage.total_requirements) * 100) 
    : 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Coverage & Duplicates</h1>
        <p className="text-sm text-gray-500 mt-1">AI-driven analysis of test gaps and redundancy.</p>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="bg-white p-6 border border-gray-200 rounded-lg shadow-sm">
          <h2 className="text-lg font-bold text-gray-800 mb-4">Requirements Coverage</h2>
          
          <div className="mb-4">
            <div className="flex justify-between mb-1">
              <span className="text-sm font-medium text-gray-700">Overall Coverage</span>
              <span className="text-sm font-bold text-blue-600">{reqPercentage}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2.5">
              <div className="bg-blue-600 h-2.5 rounded-full" style={{ width: `${reqPercentage}%` }}></div>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              {coverage.covered_requirements} of {coverage.total_requirements} requirements covered by at least one test.
            </p>
          </div>

          {coverage.untested_requirement_ids?.length > 0 && (
            <div className="mt-6">
              <h3 className="text-sm font-bold text-red-600 mb-2">Untested Requirements</h3>
              <div className="flex flex-wrap gap-2">
                {coverage.untested_requirement_ids.map((id: string) => (
                  <span key={id} className="bg-red-50 text-red-700 text-xs px-2 py-1 rounded border border-red-200">
                    {id}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="bg-white p-6 border border-gray-200 rounded-lg shadow-sm">
          <h2 className="text-lg font-bold text-gray-800 mb-4">Feature Gaps</h2>
          
          {coverage.high_risk_coverage_warning ? (
            <div className="p-4 bg-orange-50 text-orange-800 rounded-md border border-orange-200">
              <p className="font-semibold mb-2">{coverage.high_risk_coverage_warning}</p>
              <ul className="list-disc list-inside text-sm space-y-1">
                {coverage.untested_features.map((f: string) => (
                  <li key={f}>{f}</li>
                ))}
              </ul>
            </div>
          ) : (
            <div className="p-4 bg-green-50 text-green-800 rounded-md border border-green-200 text-center">
              <p className="font-medium">All planned features have test cases!</p>
            </div>
          )}
        </div>
      </div>

      <div className="bg-white p-6 border border-gray-200 rounded-lg shadow-sm">
        <h2 className="text-lg font-bold text-gray-800 mb-4">Duplicate Detector</h2>
        {duplicates.length === 0 ? (
          <p className="text-gray-500 text-sm">No duplicate test cases detected (Threshold: 85%).</p>
        ) : (
          <div className="space-y-2">
            {duplicates.map((dupe: any, idx: number) => (
              <div key={idx} className="p-3 bg-yellow-50 border border-yellow-200 rounded-md text-sm text-yellow-800 flex justify-between items-center">
                <span>Test <strong>{dupe[0]}</strong> is highly similar to Test <strong>{dupe[1]}</strong></span>
                <span className="font-bold bg-yellow-200 px-2 py-1 rounded">{Math.round(dupe[2] * 100)}% match</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
