import { Suspense } from "react";
import ClientScans from "./ClientScans";

export default async function ScansTab(props: { params: Promise<{ project_id: string }> }) {
  const params = await props.params;

  return (
    <div className="max-w-[1400px] mx-auto h-full">
      <Suspense fallback={<div className="p-8 text-center text-zinc-500">Loading scan environment...</div>}>
        <ClientScans projectId={params.project_id} />
      </Suspense>
    </div>
  );
}
