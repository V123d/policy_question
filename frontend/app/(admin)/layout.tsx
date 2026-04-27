"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import {
  LayoutDashboard,
  FileText,
  Users,
  MessageSquare,
  Tags,
  LogOut,
  Shield,
  ArrowLeft,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useEffect } from "react";

const adminNavItems = [
  { href: "/admin/dashboard", label: "仪表盘", icon: LayoutDashboard },
  { href: "/admin/policies", label: "政策管理", icon: FileText },
  { href: "/admin/users", label: "用户管理", icon: Users },
  { href: "/admin/queries", label: "问答日志", icon: MessageSquare },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { user, isAdmin, loading } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (!loading && (!user || !isAdmin)) {
      router.push("/");
    }
  }, [user, isAdmin, loading, router]);

  if (loading) return null;
  if (!user || !isAdmin) return null;

  return (
    <div className="min-h-screen bg-muted/30">
      <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur">
        <div className="container flex h-14 items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="flex items-center gap-2 text-muted-foreground hover:text-foreground">
              <ArrowLeft className="h-4 w-4" />
              <span className="text-sm">返回前台</span>
            </Link>
            <div className="h-4 w-px bg-border" />
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-primary" />
              <span className="font-semibold">管理后台</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">{user.username}</span>
            <Button variant="ghost" size="sm" onClick={() => router.push("/")} className="gap-1.5">
              <ArrowLeft className="h-4 w-4" />
              退出管理
            </Button>
          </div>
        </div>
      </header>

      <div className="flex">
        <aside className="w-56 border-r bg-background min-h-[calc(100vh-3.5rem)] p-4">
          <nav className="space-y-1">
            {adminNavItems.map((item) => (
              <Link key={item.href} href={item.href}>
                <Button
                  variant={pathname === item.href ? "secondary" : "ghost"}
                  className="w-full justify-start gap-2"
                >
                  <item.icon className="h-4 w-4" />
                  {item.label}
                </Button>
              </Link>
            ))}
          </nav>
        </aside>
        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}
