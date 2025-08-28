import { useQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { format } from "date-fns";
import { ChevronRight } from "lucide-react";
import { useMemo, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
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
	ticket_number: number;
}

function RouteComponent() {
	const { data, isSuccess, isLoading } = useQuery<ITicketResponse[]>({
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

	const [selectedTicket, setSelectedTicket] = useState<ITicketResponse | null>(
		null,
	);

	const defineContent = useMemo(() => {
		if (isLoading) {
			return <div className="p-6">Loading tickets...</div>;
		}
		if (isSuccess && data && data.length > 0) {
			return data
				.sort((a, b) => {
					return (
						new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
					);
				})
				.map((ticket) => (
					<button
						type="button"
						onClick={() => setSelectedTicket(ticket)}
						key={ticket.id}
						className={cn(
							"px-6 py-4 hover:bg-accent text-start cursor-pointer flex justify-between items-center space-x-2",
							{
								"rounded-t-xl": ticket === data[0],
								"rounded-b-xl": ticket === data[data.length - 1],
								"bg-accent": selectedTicket?.id === ticket.id,
							},
						)}
					>
						<section className="flex flex-col min-w-0">
							<div className="text-sm">{ticket.customer_id}</div>
							<h2 className="text-sm font-semibold truncate">{ticket.title}</h2>
						</section>
						<div>
							<ChevronRight className="h-4 w-4 text-muted-foreground" />
						</div>
					</button>
				));
		}
		return <div className="p-6">No tickets available.</div>;
	}, [data, isLoading, isSuccess, selectedTicket]);

	return (
		<main className="flex flex-1 flex-col py-4 md:py-6 px-4 lg:px-6 @container/main">
			<div className="flex gap-6">
				<section className="w-full max-w-xs">
					<Card className="py-0 gap-6">
						<CardContent className="px-0">
							<div className="flex flex-col divide-y">{defineContent}</div>
						</CardContent>
					</Card>
				</section>
				<section className="w-full">
					<Card>
						<CardContent className="px-0">
							{selectedTicket ? (
								<div className="space-y-4">
									<div className="px-6">
										<h2 className="text-lg font-semibold">
											{selectedTicket.title}
										</h2>
										<p className="text-sm text-muted-foreground">
											Customer ID: {selectedTicket.customer_id}
										</p>
										<p className="text-sm text-muted-foreground">
											Ticket Number: #{selectedTicket.ticket_number}
										</p>
										<p className="text-sm text-muted-foreground">
											Priority: {selectedTicket.priority}
										</p>
										<p className="text-sm text-muted-foreground">
											Status: {selectedTicket.status}
										</p>
										<p className="text-sm text-muted-foreground">
											Created At:{" "}
											{format(new Date(selectedTicket.created_at), "PPP p")}
										</p>
									</div>
									<div className="px-6">
										<h3 className="text-md font-semibold mb-2">Description</h3>
										<p className="text-sm">{selectedTicket.description}</p>
									</div>
								</div>
							) : (
								<p className="px-6">Select a ticket to view details.</p>
							)}
						</CardContent>
					</Card>
				</section>
			</div>
		</main>
	);
}
