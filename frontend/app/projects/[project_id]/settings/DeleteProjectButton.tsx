"use client";

import { useState } from "react";
import { Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useToast } from "@/components/ui/ToastProvider";
import { useConfirm } from "@/components/ui/ConfirmProvider";

export default function DeleteProjectButton({ projectId }: { projectId: string }) {
  const router = useRouter();
  const { success, error } = useToast();
  const { confirm } = useConfirm();
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDelete = async () => {
    const confirmed = await confirm({
      title: "Delete Project",
      message: "Are you absolutely sure? This will permanently delete the project and all of its data. This action cannot be undone.",
      confirmText: "Yes, delete project"
    });

    if (!confirmed) return;

    setIsDeleting(true);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/v1/projects/${projectId}`, {
        method: "DELETE"
      });

      if (res.ok) {
        success("Project deleted successfully.");
        // Redirect to projects list
        router.push("/projects");
        router.refresh();
      } else {
        error("Failed to delete project.");
        setIsDeleting(false);
      }
    } catch (e) {
      console.error(e);
      error("An error occurred while deleting the project.");
      setIsDeleting(false);
    }
  };

  return (
    <button 
      onClick={handleDelete}
      disabled={isDeleting}
      className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors border border-red-900 bg-red-950/50 text-red-400 hover:bg-red-900/50 hover:text-red-300 h-9 px-4 py-2 disabled:opacity-50 disabled:cursor-not-allowed"
    >
      <Trash2 className="mr-2 h-4 w-4" />
      {isDeleting ? "Deleting..." : "Delete Project"}
    </button>
  );
}
