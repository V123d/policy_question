"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { api, Policy } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Search, FileText, Building2, Calendar, Loader2 } from "lucide-react";

export default function PoliciesPage() {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const loadPolicies = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.policies.list();
      setPolicies(data);
    } catch {
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPolicies();
  }, [loadPolicies]);

  const filtered = policies.filter((p) => {
    const matchSearch = !search || p.name.toLowerCase().includes(search.toLowerCase());
    const matchStatus = statusFilter === "all" || p.status === statusFilter;
    return matchSearch && matchStatus;
  });

  const statusBadge = (status: string) => {
    switch (status) {
      case "active":
        return <Badge variant="success">已解析</Badge>;
      case "parsing":
        return <Badge variant="warning">解析中</Badge>;
      case "failed":
        return <Badge variant="destructive">失败</Badge>;
      default:
        return <Badge>{status}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">政策库</h1>
          <p className="text-sm text-muted-foreground">浏览所有已解析的政策文件</p>
        </div>
        <div className="flex gap-2 w-full md:w-auto">
          <div className="relative flex-1 md:w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="搜索政策名称..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-32">
              <SelectValue placeholder="状态" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部状态</SelectItem>
              <SelectItem value="active">已解析</SelectItem>
              <SelectItem value="parsing">解析中</SelectItem>
              <SelectItem value="failed">失败</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-20 text-muted-foreground">
          <FileText className="h-12 w-12 mx-auto mb-4 opacity-30" />
          <p>暂无政策文件</p>
          <p className="text-sm">请管理员上传政策文件</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((policy) => (
            <Link key={policy.id} href={`/policies/${policy.id}`}>
              <Card className="h-full hover:shadow-md transition-shadow cursor-pointer">
                <CardContent className="p-5">
                  <div className="flex items-start justify-between gap-2 mb-3">
                    <div className="flex-1 min-w-0">
                      <h3 className="font-medium leading-tight line-clamp-2">{policy.name}</h3>
                    </div>
                    {statusBadge(policy.status)}
                  </div>

                  <div className="space-y-1.5 text-sm text-muted-foreground">
                    {policy.issuing_body && (
                      <div className="flex items-center gap-1.5">
                        <Building2 className="h-3.5 w-3.5 flex-shrink-0" />
                        <span className="truncate">{policy.issuing_body}</span>
                      </div>
                    )}
                    {policy.deadline && (
                      <div className="flex items-center gap-1.5">
                        <Calendar className="h-3.5 w-3.5 flex-shrink-0" />
                        <span>申报截止：{policy.deadline}</span>
                      </div>
                    )}
                  </div>

                  <div className="flex gap-1.5 mt-3 flex-wrap">
                    {policy.doc_type && (
                      <Badge variant="outline" className="text-xs">
                        {policy.doc_type}
                      </Badge>
                    )}
                    {policy.policy_level && (
                      <Badge variant="outline" className="text-xs">
                        {policy.policy_level}
                      </Badge>
                    )}
                  </div>

                  {policy.structured_data && Object.keys(policy.structured_data).length > 0 && (
                    <p className="text-xs text-muted-foreground mt-3">
                      {Object.keys(policy.structured_data).length} 个结构化字段
                    </p>
                  )}
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
