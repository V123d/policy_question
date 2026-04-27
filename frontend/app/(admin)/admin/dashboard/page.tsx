"use client";

import { useState, useEffect, useCallback } from "react";
import { api, DashboardStats } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Loader2, FileText, Users, MessageSquare, CheckCircle, XCircle, Clock, RefreshCw, AlertTriangle, Wifi } from "lucide-react";
import Link from "next/link";

export default function AdminDashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadStats = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.admin.dashboard();
      setStats(data);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "未知错误";
      setError(msg);
      console.error("[Dashboard] 加载失败:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        <p className="text-sm text-muted-foreground">加载管理数据中...</p>
      </div>
    );
  }

  if (error) {
    const isAuthError = error.includes("Unauthorized") || error.includes("401") || error.includes("token");
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4 text-center max-w-md mx-auto">
        <div className="w-16 h-16 rounded-full bg-destructive/10 flex items-center justify-center">
          <AlertTriangle className="h-8 w-8 text-destructive" />
        </div>
        <div>
          <p className="font-semibold text-foreground">加载失败</p>
          <p className="text-sm text-muted-foreground mt-1">{error}</p>
        </div>
        {isAuthError && (
          <p className="text-xs text-muted-foreground bg-muted px-3 py-2 rounded-md">
            请确认已以管理员账号登录，并确保后端服务已启动。
          </p>
        )}
        <div className="flex gap-2 mt-2">
          <button
            onClick={loadStats}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:opacity-90 transition-opacity"
          >
            <RefreshCw className="h-4 w-4" />
            重试
          </button>
          <Link href="/">
            <button className="flex items-center gap-2 px-4 py-2 border border-border rounded-md text-sm font-medium hover:bg-muted transition-colors">
              返回首页
            </button>
          </Link>
        </div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="text-center py-20">
        <p className="text-muted-foreground">暂无数据</p>
        <button onClick={loadStats} className="mt-2 text-sm text-primary hover:underline">
          重新加载
        </button>
      </div>
    );
  }

  const statCards = [
    {
      title: "政策总数",
      value: stats.total_policies,
      icon: FileText,
      color: "text-blue-600 bg-blue-50",
    },
    {
      title: "已解析",
      value: stats.active_policies,
      icon: CheckCircle,
      color: "text-green-600 bg-green-50",
    },
    {
      title: "解析中",
      value: stats.parsing_policies,
      icon: Clock,
      color: "text-yellow-600 bg-yellow-50",
    },
    {
      title: "解析失败",
      value: stats.failed_policies,
      icon: XCircle,
      color: "text-red-600 bg-red-50",
    },
    {
      title: "用户总数",
      value: stats.total_users,
      icon: Users,
      color: "text-purple-600 bg-purple-50",
    },
    {
      title: "今日问答",
      value: stats.chats_today,
      icon: MessageSquare,
      color: "text-orange-600 bg-orange-50",
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">管理仪表盘</h1>
          <p className="text-sm text-muted-foreground">系统运行概览</p>
        </div>
        <button
          onClick={loadStats}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground border border-border rounded-md hover:bg-muted transition-colors"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          刷新
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {statCards.map((card) => (
          <Card key={card.title} className="hover:shadow-md transition-shadow">
            <CardContent className="p-4">
              <div className="flex items-center justify-between mb-2">
                <span className={`p-2 rounded-lg ${card.color}`}>
                  <card.icon className="h-4 w-4" />
                </span>
              </div>
              <p className="text-2xl font-bold">{card.value}</p>
              <p className="text-xs text-muted-foreground">{card.title}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">本周问答量</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{stats.chats_this_week}</div>
            <p className="text-xs text-muted-foreground">近7天问答总数</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">累计问答量</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{stats.total_chats}</div>
            <p className="text-xs text-muted-foreground">系统累计问答总数</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">解析成功率</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{stats.parse_success_rate}%</div>
            <div className="mt-2 h-2 bg-muted rounded-full overflow-hidden">
              <div
                className="h-full bg-green-500 transition-all"
                style={{ width: `${stats.parse_success_rate}%` }}
              />
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {stats.active_policies} / {stats.total_policies} 政策解析成功
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
