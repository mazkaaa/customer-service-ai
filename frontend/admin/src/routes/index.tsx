import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/")({
	component: App,
});

function App() {
	return (
		<main className="flex flex-1 flex-col py-4 md:py-6 px-4 lg:px-6 @container/main">
			<h1>test</h1>
		</main>
	);
}
