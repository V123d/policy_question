"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import {
  MessageSquare,
  BookOpen,
  Calendar,
  LayoutDashboard,
  LogOut,
  Shield,
  Menu,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useState } from "react";

const navItems = [
  { href: "/", label: "首页", icon: BookOpen },
  { href: "/chat", label: "智能问答", icon: MessageSquare },
  { href: "/policies", label: "政策库", icon: BookOpen },
  { href: "/timeline", label: "申报时间轴", icon: Calendar },
];

export function Navigation() {
  const { user, logout, isAdmin } = useAuth();
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  if (!user) return null;
  if (pathname.startsWith("/login") || pathname.startsWith("/register")) return null;

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield className="h-6 w-6 text-primary" />
          <Link href="/" className="text-lg font-semibold">
            政策问答智能体
          </Link>
        </div>

        <nav className="hidden md:flex items-center gap-1">
          {navItems.map((item) => (
            <Link key={item.href} href={item.href}>
              <Button
                variant={pathname === item.href ? "secondary" : "ghost"}
                size="sm"
                className="gap-1.5"
              >
                <item.icon className="h-4 w-4" />
                {item.label}
              </Button>
            </Link>
          ))}
          {isAdmin && (
            <Link href="/admin/dashboard">
              <Button
                variant={pathname.startsWith("/admin") ? "secondary" : "ghost"}
                size="sm"
                className="gap-1.5"
              >
                <LayoutDashboard className="h-4 w-4" />
                管理后台
              </Button>
            </Link>
          )}
        </nav>

        <div className="flex items-center gap-2">
          <span className="hidden md:inline text-sm text-muted-foreground">
            {user.username}
          </span>
          {isAdmin && (
            <span className="hidden md:inline text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-full">
              管理员
            </span>
          )}
          <Button variant="ghost" size="sm" onClick={logout} className="gap-1.5">
            <LogOut className="h-4 w-4" />
            <span className="hidden md:inline">退出</span>
          </Button>
        </div>

        <button className="md:hidden" onClick={() => setMobileOpen(!mobileOpen)}>
          {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {mobileOpen && (
        <div className="md:hidden border-t p-4 space-y-1">
          {navItems.map((item) => (
            <Link key={item.href} href={item.href} onClick={() => setMobileOpen(false)}>
              <Button variant={pathname === item.href ? "secondary" : "ghost"} className="w-full justify-start gap-2">
                <item.icon className="h-4 w-4" />
                {item.label}
              </Button>
            </Link>
          ))}
          {isAdmin && (
            <Link href="/admin/dashboard" onClick={() => setMobileOpen(false)}>
              <Button variant={pathname.startsWith("/admin") ? "secondary" : "ghost"} className="w-full justify-start gap-2">
                <LayoutDashboard className="h-4 w-4" />
                管理后台
              </Button>
            </Link>
          )}
        </div>
      )}
    </header>
  );
}
