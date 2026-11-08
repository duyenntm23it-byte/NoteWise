import type { Metadata } from "next";

import { AnalyticsWorkspace } from "@/components/analytics-workspace";

export const metadata: Metadata = {
  title: "Analytics",
  description: "Review quiz performance and find learning topics that need more practice.",
};

export default function DashboardAnalyticsPage() {
  return <AnalyticsWorkspace />;
}
