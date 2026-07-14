import ClientComparisons from "./ClientComparisons";

export default async function ComparisonsTab(props: { params: Promise<{ project_id: string }> }) {
  const params = await props.params;
  
  return (
    <div className="h-full">
      <ClientComparisons projectId={params.project_id} />
    </div>
  );
}
