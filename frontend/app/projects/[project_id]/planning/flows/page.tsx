"use client";

import { useEffect, useState } from "react";

export default function FlowsPage({ params }: { params: { project_id: string } }) {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`http://localhost:8000/api/v1/projects/${params.project_id}/planning/flows`)
      .then((res) => {
        if (!res.ok) throw new Error("No data found");
        return res.json();
      })
      .then((d) => setData(d))
      .catch((err) => setError(err.message));
  }, [params.project_id]);

  if (error) return <div className="text-gray-500 italic">No flows data found. Generate a plan first.</div>;
  if (!data) return <div>Loading...</div>;

  return (
    <div className="bg-white p-8 rounded-lg shadow-sm border border-gray-200">
      <h1 className="text-2xl font-bold mb-6 text-purple-700">Critical User Flows</h1>
      <div className="space-y-8">
        {data.user_flows?.map((flow: any, idx: number) => (
          <div key={idx} className="border border-gray-200 rounded p-6">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h2 className="text-xl font-bold">{flow.name}</h2>
                <div className="text-sm text-gray-500 mt-1">Feature: {flow.feature_name}</div>
              </div>
              <div className="bg-green-100 text-green-800 text-xs px-3 py-1 rounded-full font-medium">
                {flow.business_value}
              </div>
            </div>
            
            <div className="space-y-3 mt-4">
              {flow.steps?.map((step: any, sIdx: number) => (
                <div key={sIdx} className="flex gap-4 p-3 bg-gray-50 rounded">
                  <div className="font-mono text-gray-400 font-bold">{step.step_number}.</div>
                  <div>
                    <div className="font-semibold text-gray-800">{step.action}</div>
                    <div className="text-sm text-gray-600">{step.description}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
