"use client";

import { useEffect, useState } from "react";

export default function StrategyPage({ params }: { params: { project_id: string } }) {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/v1/projects/${params.project_id}/planning/strategy`)
      .then((res) => {
        if (!res.ok) throw new Error("No data found");
        return res.json();
      })
      .then((d) => setData(d))
      .catch((err) => setError(err.message));
  }, [params.project_id]);

  if (error) return <div className="text-gray-500 italic">No strategy data found. Generate a plan first.</div>;
  if (!data) return <div>Loading...</div>;

  return (
    <div className="bg-white p-8 rounded-lg shadow-sm border border-gray-200">
      <h1 className="text-2xl font-bold mb-6 text-purple-700">Testing Strategy</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {data.strategies?.map((strat: any, idx: number) => (
          <div key={idx} className="border border-gray-200 rounded p-6 shadow-sm">
            <h2 className="text-xl font-bold mb-4 border-b pb-2">{strat.feature_name}</h2>
            <div className="mb-4">
              <h3 className="text-sm font-bold text-gray-500 uppercase mb-2">Recommended Approaches</h3>
              <div className="flex flex-wrap gap-2">
                {strat.recommended_strategies.map((rs: string, rsIdx: number) => (
                  <span key={rsIdx} className="bg-indigo-100 text-indigo-800 text-xs px-2 py-1 rounded">
                    {rs}
                  </span>
                ))}
              </div>
            </div>
            <div>
              <h3 className="text-sm font-bold text-gray-500 uppercase mb-1">Justification</h3>
              <p className="text-sm text-gray-700 leading-relaxed">{strat.justification}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
