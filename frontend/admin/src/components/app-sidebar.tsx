import { Link } from "@tanstack/react-router";
import {
	Bot,
	BotMessageSquare,
	Camera,
	ChartBar,
	Database,
	File,
	Files,
	FilesIcon,
	HelpCircle,
	LayoutDashboard,
	Search,
	Settings,
	Ticket,
	Users,
} from "lucide-react";
import type * as React from "react";
import { NavDocuments } from "@/components/nav-documents";
import { NavMain } from "@/components/nav-main";
import { NavSecondary } from "@/components/nav-secondary";
import { NavUser } from "@/components/nav-user";
import {
	Sidebar,
	SidebarContent,
	SidebarFooter,
	SidebarHeader,
	SidebarMenu,
	SidebarMenuButton,
	SidebarMenuItem,
} from "@/components/ui/sidebar";

const data = {
	user: {
		name: "admin",
		email: "admin@example.com",
		avatar: "/avatars/shadcn.jpg",
	},
	navMain: [
		{
			title: "Dashboard",
			url: "/",
			icon: <LayoutDashboard />,
		},
		{
			title: "Analytics",
			url: "#",
			icon: <ChartBar />,
		},
		{
			title: "Assistant",
			url: "#",
			icon: <Bot />,
		},
		{
			title: "Team",
			url: "#",
			icon: <Users />,
		},
	],
	navClouds: [
		{
			title: "Capture",
			icon: <Camera />,
			isActive: true,
			url: "#",
			items: [
				{
					title: "Active Proposals",
					url: "#",
				},
				{
					title: "Archived",
					url: "#",
				},
			],
		},
		{
			title: "Proposal",
			icon: <File />,
			url: "#",
			items: [
				{
					title: "Active Proposals",
					url: "#",
				},
				{
					title: "Archived",
					url: "#",
				},
			],
		},
		{
			title: "Prompts",
			icon: <Bot />,
			url: "#",
			items: [
				{
					title: "Active Proposals",
					url: "#",
				},
				{
					title: "Archived",
					url: "#",
				},
			],
		},
	],
	navSecondary: [
		{
			title: "Settings",
			url: "#",
			icon: <Settings />,
		},
		{
			title: "Get Help",
			url: "#",
			icon: <HelpCircle />,
		},
		{
			title: "Search",
			url: "#",
			icon: <Search />,
		},
	],
	documents: [
		{
			name: "Tickets",
			url: "/tickets",
			icon: <Ticket />,
		},
		{
			name: "Knowledge Library",
			url: "#",
			icon: <Database />,
		},
	],
};

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
	return (
		<Sidebar collapsible="offcanvas" {...props}>
			<SidebarHeader>
				<SidebarMenu>
					<SidebarMenuItem>
						<SidebarMenuButton
							asChild
							className="data-[slot=sidebar-menu-button]:!p-1.5"
						>
							<Link to="/">
								<BotMessageSquare className="!size-5" />
								<span className="text-base font-semibold">Admin Panel</span>
							</Link>
						</SidebarMenuButton>
					</SidebarMenuItem>
				</SidebarMenu>
			</SidebarHeader>
			<SidebarContent>
				<NavMain items={data.navMain} />
				<NavDocuments items={data.documents} />
				<NavSecondary items={data.navSecondary} className="mt-auto" />
			</SidebarContent>
			<SidebarFooter>
				<NavUser user={data.user} />
			</SidebarFooter>
		</Sidebar>
	);
}
