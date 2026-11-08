import type { Metadata } from "next";

import { MaterialsHub } from "@/components/materials-hub";

export const metadata: Metadata = {
  title: "Material Hub",
  description: "Upload and manage your NoteWise learning materials.",
};

export default function DashboardMaterialsPage() {
  return <MaterialsHub />;
}
