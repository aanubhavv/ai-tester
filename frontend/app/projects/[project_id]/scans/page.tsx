import ClientScans from "./ClientScans";

export default async function ScansTab(props: { params: Promise<{ project_id: string }> }) {
  const params = await props.params;

  return (
    <div className="max-w-[1400px] mx-auto h-full">
      <ClientScans projectId={params.project_id} />
    </div>
  );
}
