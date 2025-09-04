import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import type { ColumnDef } from "@tanstack/react-table";
import { Brain, Check, Loader2Icon, Trash } from "lucide-react";
import { useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { DataTable } from "@/components/data-table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/knowledge/")({
  component: RouteComponent,
});

interface IKnowledgeFileResponse {
  filename: string;
  extension: string;
  is_processed: boolean;
  upload_date: number;
  size_bytes: number;
  chunks_in_vector_db: number;
}

interface IKnowledgeFilesBasicResponse {
  filename: string;
  message: string;
}

interface IKnowledgeFilesProccededResponse
  extends IKnowledgeFilesBasicResponse {
  chunks_added: number;
}

function RouteComponent() {
  const [file, setFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const knowledgeFilesQuery = useQuery<{ files: IKnowledgeFileResponse[] }>({
    queryKey: ["knowledge-files"],
    queryFn: async (): Promise<{ files: IKnowledgeFileResponse[] }> => {
      const response = await fetch(import.meta.env.VITE_API_URL + "/knowledge");
      if (!response.ok) {
        throw new Error("Network response was not ok");
      }
      const result = await response.json();
      return result;
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
    gcTime: 1000 * 60 * 10, // 10 minutes
  });

  const queryClient = useQueryClient();

  const uploadFileMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(
        import.meta.env.VITE_API_URL + "/knowledge",
        {
          method: "POST",
          body: formData,
        }
      );
      if (!response.ok) {
        throw new Error("Network response was not ok");
      }
      const result = await response.json();
      return result as IKnowledgeFilesBasicResponse;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["knowledge-files"] });
      setFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      toast.success("File uploaded successfully");
    },
  });

  const processFileMutation = useMutation({
    mutationFn: async (payload: {
      file_name: string;
      add_to_vector_db: boolean;
    }) => {
      const response = await fetch(
        import.meta.env.VITE_API_URL + "/knowledge",
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            file_name: payload.file_name,
            add_to_vector_db: payload.add_to_vector_db,
          }),
        }
      );
      const result = await response.json();
      if (!response.ok) {
        throw result;
      }
      return result as IKnowledgeFilesProccededResponse;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["knowledge-files"] });
      toast.success("File added to the agent knowledge successfully");
    },
    onError: () => {
      toast.error("Error processing file");
    },
  });

  const deleteFileMutation = useMutation({
    mutationFn: async (payload: { filename: string }) => {
      const response = await fetch(
        import.meta.env.VITE_API_URL + `/knowledge/${payload.filename}`,
        {
          method: "DELETE",
        }
      );
      if (!response.ok) {
        throw new Error("Network response was not ok");
      }
      const result = await response.json();
      return result as IKnowledgeFilesBasicResponse;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["knowledge-files"] });
      toast.success("File deleted successfully");
    },
  });

  const column = useMemo<ColumnDef<IKnowledgeFileResponse>[]>(
    () => [
      {
        accessorKey: "filename",
        header: "Filename",
      },
      {
        accessorKey: "is_processed",
        header: "Agent Knowledge",
        cell: ({ getValue }) =>
          getValue() ? <Badge>Yes</Badge> : <Badge variant="outline">No</Badge>,
      },
      // {
      // 	accessorKey: "upload_date",
      // 	header: "Upload Date",
      // 	cell: ({ getValue }) => format(new Date(getValue() as number), "PPpp"),
      // },
      // {
      // 	accessorKey: "size_bytes",
      // 	header: "Size (bytes)",
      // },
      {
        accessorKey: "chunks_in_vector_db",
        header: "Chunks Vector DB",
      },
      {
        id: "actions",
        header: "Actions",
        cell: ({ row }) => {
          const filename = row.original.filename;
          return (
            <div className="flex gap-2">
              <Button
                size="icon"
                disabled={
                  processFileMutation.isPending || deleteFileMutation.isPending
                }
                variant={row.original.is_processed ? "outline" : "default"}
                onClick={() =>
                  processFileMutation.mutate({
                    file_name: filename,
                    add_to_vector_db: !row.original.is_processed,
                  })
                }
              >
                {processFileMutation.isPending ? (
                  <Loader2Icon className="animate-spin" />
                ) : row.original.is_processed ? (
                  <Check />
                ) : (
                  <Brain />
                )}
              </Button>
              <Button
                onClick={() => {
                  deleteFileMutation.mutate({ filename });
                }}
                size={"icon"}
                variant={"destructive"}
                disabled={
                  processFileMutation.isPending || deleteFileMutation.isPending
                }
              >
                {deleteFileMutation.isPending ? (
                  <Loader2Icon className="animate-spin" />
                ) : (
                  <Trash />
                )}
              </Button>
            </div>
          );
        },
      },
    ],
    [processFileMutation.isPending, processFileMutation, deleteFileMutation]
  );

  return (
    <main className="flex flex-1 flex-col py-4 md:py-6 px-4 lg:px-6 @container/main">
      <div className="grid grid-cols-4 gap-4">
        <section className="col-span-1">
          <div className="border rounded-lg h-80 flex flex-col justify-center items-center text-center gap-4 p-4">
            <div className="gap-4 flex flex-col">
              <div className="max-w-xs gap-2 flex flex-col">
                <h3 className="text-sm text-muted-foreground">
                  Drag and drop a file here to upload or click the button below
                  to select a file.
                </h3>
                {file && (
                  <p className="text-sm text-muted-foreground">
                    Selected file:{" "}
                    <span className="font-semibold">{file.name}</span>
                  </p>
                )}
              </div>
              <div className="flex flex-row gap-2 justify-center">
                {file && (
                  <Button
                    onClick={() => {
                      uploadFileMutation.mutate(file);
                    }}
                    size={"sm"}
                    disabled={uploadFileMutation.isPending}
                  >
                    {uploadFileMutation.isPending ? (
                      <>
                        <Loader2Icon className="animate-spin" />
                        Uploading...
                      </>
                    ) : (
                      "Upload File"
                    )}
                  </Button>
                )}
                <Button
                  onClick={() => fileInputRef.current?.click()}
                  size={"sm"}
                  variant={"outline"}
                >
                  Select File
                </Button>
              </div>
              <input
                accept=".pdf,.docx,.txt"
                type="file"
                ref={fileInputRef}
                className="hidden"
                onChange={(e) => {
                  if (e.target.files && e.target.files.length > 0) {
                    const selectedFile = e.target.files[0];
                    setFile(selectedFile);
                  }
                }}
              />
            </div>
          </div>
        </section>
        <section className="col-span-3">
          <DataTable
            columns={column}
            data={knowledgeFilesQuery.data?.files ?? []}
            isLoading={knowledgeFilesQuery.isLoading}
          />
        </section>
      </div>
    </main>
  );
}
