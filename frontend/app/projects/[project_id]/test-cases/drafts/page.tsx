"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";

export default function DraftsPage() {
  const { project_id } = useParams();
  const [testCases, setTestCases] = useState<any[]>([]);
  const [suites, setSuites] = useState<any[]>([]);
  const [selectedSuite, setSelectedSuite] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, [project_id]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [tcRes, suitesRes] = await Promise.all([
        fetch(`http://localhost:8000/api/v1/projects/${project_id}/test-cases`),
        fetch(`http://localhost:8000/api/v1/projects/${project_id}/planning/suites`),
      ]);
      
      if (tcRes.ok) {
        const data = await tcRes.json();
        setTestCases(data.filter((tc: any) => tc.status === "Draft" || tc.status === "Reviewed"));
      }
      
      if (suitesRes.ok) {
        const data = await suitesRes.json();
        setSuites(data.suites || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    if (!selectedSuite) return alert("Select a suite first.");
    try {
      const res = await fetch(`http://localhost:8000/api/v1/projects/${project_id}/test-cases/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ feature_name: "", suite_name: selectedSuite }) // Backend looks up feature anyway
      });
      if (res.ok) {
        alert("Generation started! This will take a few seconds in the background.");
      } else {
        alert("Failed to start generation.");
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleApprove = async (testId: string) => {
    try {
      const res = await fetch(`http://localhost:8000/api/v1/projects/${project_id}/test-cases/${testId}/approve`, {
        method: "POST"
      });
      if (res.ok) {
        // Remove from list
        setTestCases(testCases.filter((tc) => tc.id !== testId));
      }
    } catch (e) {
      console.error(e);
    }
  };

  if (loading) return <div className="animate-pulse">Loading drafts...</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Draft Test Cases</h1>
          <p className="text-sm text-gray-500 mt-1">Review AI-generated test cases before approving them for automation.</p>
        </div>
        
        <div className="flex gap-2">
          <select 
            value={selectedSuite}
            onChange={(e) => setSelectedSuite(e.target.value)}
            className="border-gray-300 rounded-md text-sm shadow-sm focus:border-green-500 focus:ring-green-500"
          >
            <option value="">Select Suite to Generate...</option>
            {suites.map((s) => (
              <option key={s.suite_name} value={s.suite_name}>{s.suite_name}</option>
            ))}
          </select>
          <button 
            onClick={handleGenerate}
            className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-md text-sm font-medium transition"
          >
            Generate AI Tests
          </button>
        </div>
      </div>

      {testCases.length === 0 ? (
        <div className="bg-white p-8 rounded-lg border border-gray-200 text-center text-gray-500">
          No draft test cases found. Select a suite and click Generate to start!
        </div>
      ) : (
        <div className="grid gap-4">
          {testCases.map((tc) => (
            <div key={tc.id} className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm flex flex-col">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs font-mono bg-gray-100 text-gray-600 px-2 py-1 rounded">v{tc.version}</span>
                    <span className={`text-xs px-2 py-1 rounded font-medium ${
                      tc.priority === 'Critical' ? 'bg-red-100 text-red-700' :
                      tc.priority === 'High' ? 'bg-orange-100 text-orange-700' :
                      tc.priority === 'Medium' ? 'bg-yellow-100 text-yellow-700' :
                      'bg-green-100 text-green-700'
                    }`}>{tc.priority}</span>
                    <span className="text-xs px-2 py-1 rounded font-medium bg-blue-100 text-blue-700">{tc.type}</span>
                    <span className="text-xs text-gray-500">&middot; {tc.traceability.test_suite_name}</span>
                  </div>
                  <h3 className="text-lg font-bold text-gray-900">{tc.title}</h3>
                  <p className="text-gray-600 mt-1 text-sm">{tc.description}</p>
                </div>
                <button
                  onClick={() => handleApprove(tc.id)}
                  className="bg-gray-900 hover:bg-gray-800 text-white px-3 py-1.5 rounded text-sm transition"
                >
                  Approve
                </button>
              </div>

              <div className="mt-4 pt-4 border-t border-gray-100 grid grid-cols-2 gap-4 text-sm">
                <div>
                  <h4 className="font-semibold text-gray-900 mb-2">Steps</h4>
                  <ul className="space-y-2">
                    {tc.steps.map((step: any, idx: number) => (
                      <li key={idx} className="flex gap-2 text-gray-700">
                        <span className="font-mono text-gray-400">{step.step_number}.</span>
                        <div>
                          <p>{step.action}</p>
                          <p className="text-gray-500 italic">Expected: {step.expected_result}</p>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h4 className="font-semibold text-gray-900 mb-2">Traceability</h4>
                  <div className="space-y-1 text-gray-600">
                    <p><span className="font-medium text-gray-700">Feature:</span> {tc.traceability.feature_name}</p>
                    <p><span className="font-medium text-gray-700">Requirements:</span> {tc.traceability.requirement_ids?.join(', ') || 'None'}</p>
                    {tc.preconditions && (
                      <div className="mt-3">
                        <h4 className="font-semibold text-gray-900">Preconditions</h4>
                        <p>{tc.preconditions}</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
