"use client";

import { useEffect, useState } from "react";

export default function SuitesPage({ params }: { params: { project_id: string } }) {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`http://localhost:8000/api/v1/projects/${params.project_id}/planning/suites`)
      .then((res) => {
        if (!res.ok) throw new Error("No data found");
        return res.json();
      })
      .then((d) => setData(d))
      .catch((err) => setError(err.message));
  }, [params.project_id]);

  if (error) return <div className="text-gray-500 italic">No suites data found. Generate a plan first.</div>;
  if (!data) return <div>Loading...</div>;

  return (
    <div className="bg-white p-8 rounded-lg shadow-sm border border-gray-200">
      <h1 className="text-2xl font-bold mb-6 text-purple-700">Test Suites</h1>
      <div className="space-y-6">
        {data.suites?.map((suite: any, idx: number) => (
          <div key={idx} className="border border-gray-200 rounded p-6 bg-gray-50">
            <div className="flex justify-between items-center mb-2">
              <h2 className="text-xl font-bold text-gray-900">{suite.suite_name}</h2>
              <span className="text-sm text-gray-500 font-medium px-2 py-1 bg-gray-200 rounded">
                Feature: {suite.feature_name}
              </span>
            </div>
            <p className="text-gray-600 text-sm mb-4">{suite.description}</p>
            
            <div className="bg-white border border-gray-200 rounded p-4">
              <h3 className="text-sm font-bold text-gray-700 mb-3">High-Level Scenarios</h3>
              <ul className="list-disc pl-5 space-y-2 text-sm text-gray-800">
                {suite.high_level_test_cases.map((tc: string, tcIdx: number) => (
                  <li key={tcIdx}>{tc}</li>
                ))}
              </ul>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
