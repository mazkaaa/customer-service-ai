import { useQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import type { ColumnDef } from "@tanstack/react-table";
import { ChevronRight } from "lucide-react";
import { useMemo } from "react";
import { DataTable } from "@/components/data-table";
import {
	Card,
	CardContent,
	CardDescription,
	CardFooter,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/tickets/")({
	component: RouteComponent,
});

interface ITicketResponse {
	id: string;
	customer_id: string;
	title: string;
	description: string;
	priority: string;
	status: string;
	created_at: string;
}

function RouteComponent() {
	const { data, isSuccess } = useQuery<ITicketResponse[]>({
		queryKey: ["tickets"],
		queryFn: async (): Promise<ITicketResponse[]> => {
			const response = await fetch("http://localhost:8000/tickets");
			if (!response.ok) {
				throw new Error("Network response was not ok");
			}
			const result = await response.json();
			return result.tickets;
		},
	});

	return (
		<main className="flex flex-1 flex-col py-4 md:py-6 px-4 lg:px-6 @container/main">
			<div className="flex gap-6">
				<section className="w-full max-w-xs">
					<Card className="py-0 gap-6">
						<CardContent className="px-0">
							<div className="flex flex-col divide-y">
								{isSuccess ? (
									data.map((ticket) => (
										<div
											key={ticket.id}
											className={cn(
												"px-6 py-4 hover:bg-accent cursor-pointer flex justify-between items-center space-x-2",
												{
													"rounded-t-xl": ticket === data[0],
													"rounded-b-xl": ticket === data[data.length - 1],
												},
											)}
										>
											<section>
												<div className="text-sm">{ticket.customer_id}</div>
												<h2 className="text-sm font-semibold">
													{ticket.title}
												</h2>
											</section>
											<div>
												<ChevronRight className="h-4 w-4 text-muted-foreground" />
											</div>
										</div>
									))
								) : (
									<p>Loading tickets...</p>
								)}
							</div>
						</CardContent>
					</Card>
				</section>
				<section className="w-full">
					<h1 className="text-2xl font-semibold">Tickets</h1>
				</section>
			</div>
		</main>
	);
}
