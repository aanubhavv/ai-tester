import ClientTestCases from "./ClientTestCases";

async function getTestCases(projectId: string) {
  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/v1/projects/${projectId}/test-cases`, { cache: 'no-store' });
    if (!res.ok) return [];
    return res.json();
  } catch (error) {
    return [];
  }
}

export default async function TestCasesTab(props: { params: Promise<{ project_id: string }> }) {
  const params = await props.params;
  const testCases = await getTestCases(params.project_id);

  return (
    <div className="max-w-[1400px] mx-auto h-full">
      <ClientTestCases initialTestCases={testCases} projectId={params.project_id} />
    </div>
  );
}
