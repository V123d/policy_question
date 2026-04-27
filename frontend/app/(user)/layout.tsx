import { Navigation } from "@/components/Navigation";

export default function UserLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-background">
      <Navigation />
      <main className="container py-6">{children}</main>
    </div>
  );
}
