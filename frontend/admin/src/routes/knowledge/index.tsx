import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import type { ColumnDef } from "@tanstack/react-table";
import { format } from "date-fns";
import { Loader2Icon } from "lucide-react";
import { useMemo } from "react";
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

interface IKnowledgeFilesProccededResponse {
	filename: string;
	chunks_added: number;
	message: string;
}

interface IKnowledgeFilesUploadResponse {
	filename: string;
	message: string;
}

function RouteComponent() {
	const knowledgeFilesQuery = useQuery<{ files: IKnowledgeFileResponse[] }>({
		queryKey: ["knowledge-files"],
		queryFn: async (): Promise<{ files: IKnowledgeFileResponse[] }> => {
			const response = await fetch("http://localhost:8000/knowledge");
			if (!response.ok) {
				throw new Error("Network response was not ok");
			}
			const result = await response.json();
			return result;
		},
	});

	const queryClient = useQueryClient();

	const uploadFileMutation = useMutation({
		mutationFn: async (file: File) => {
			const formData = new FormData();
			formData.append("file", file);

			const response = await fetch("http://localhost:8000/knowledge", {
				method: "POST",
				body: formData,
			});
			if (!response.ok) {
				throw new Error("Network response was not ok");
			}
			const result = await response.json();
			return result as IKnowledgeFilesUploadResponse;
		},
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["knowledge-files"] });
		},
	});

	const processFileMutation = useMutation({
		mutationFn: async (payload: { filename: string }) => {
			const response = await fetch("http://localhost:8000/knowledge", {
				method: "PUT",
				headers: {
					"Content-Type": "application/json",
				},
				body: JSON.stringify({
					filename: payload.filename,
				}),
			});
			if (!response.ok) {
				throw new Error("Network response was not ok");
			}
			const result = await response.json();
			return result as IKnowledgeFilesProccededResponse;
		},
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["knowledge-files"] });
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
				header: "Processed",
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
						<Button
							size="sm"
							disabled={
								processFileMutation.isPending || row.original.is_processed
							}
							variant={row.original.is_processed ? "secondary" : "default"}
							onClick={() => processFileMutation.mutate({ filename })}
						>
							{processFileMutation.isPending && (
								<>
									<Loader2Icon className="animate-spin" />
									Processing...
								</>
							)}
							{row.original.is_processed ? "Processed" : "Process"}
						</Button>
					);
				},
			},
		],
		[processFileMutation.isPending, processFileMutation],
	);

	return (
		<main className="flex flex-1 flex-col py-4 md:py-6 px-4 lg:px-6 @container/main">
			<div className="grid grid-cols-2 gap-4">
				<DataTable
					columns={column}
					data={knowledgeFilesQuery.data?.files ?? []}
				/>
				<div>
					<h1>Upload</h1>
				</div>
			</div>
		</main>
	);
}
