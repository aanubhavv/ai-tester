"use client";

import { useEffect, useState } from "react";

export default function FeaturesPage({ params }: { params: { project_id: string } }) {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/v1/projects/${params.project_id}/planning/features`)
      .then((res) => {
        if (!res.ok) throw new Error("No data found");
        return res.json();
      })
      .then((d) => setData(d))
      .catch((err) => setError(err.message));
  }, [params.project_id]);

  if (error) return <div className="text-gray-500 italic">No features data found. Generate a plan first.</div>;
  if (!data) return <div>Loading...</div>;

  return (
    <div className="bg-white p-8 rounded-lg shadow-sm border border-gray-200">
      <h1 className="text-2xl font-bold mb-6 text-purple-700">Extracted Features</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {data.features?.map((feat: any, idx: number) => (
          <div key={idx} className="border border-gray-200 rounded p-4 hover:shadow-md transition">
            <h2 className="text-lg font-bold mb-2">{feat.name}</h2>
            <p className="text-gray-600 text-sm mb-4">{feat.description}</p>
            <div className="text-xs text-gray-400">
              <strong>Covers Requirements:</strong> {feat.related_requirements.join(", ")}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
