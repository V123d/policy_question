"use client";

import { useState, useEffect, useCallback } from "react";
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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Upload, FileText, Trash2, RefreshCw, Loader2, Search, CheckCircle } from "lucide-react";
import { useRef } from "react";

export default function AdminPoliciesPage() {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [deleteTarget, setDeleteTarget] = useState<Policy | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [reparsing, setReparsing] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadPolicies = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.admin.listPolicies();
      setPolicies(data);
    } catch {} finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPolicies();
  }, [loadPolicies]);

  const handleUpload = async (file: File) => {
    setUploading(true);
    try {
      await api.admin.uploadPolicy(file);
      await loadPolicies();
    } catch (err) {
      alert(`上传失败: ${err}`);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await api.admin.deletePolicy(deleteTarget.id);
      setPolicies(policies.filter((p) => p.id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch (err) {
      alert(`删除失败: ${err}`);
    } finally {
      setDeleting(false);
    }
  };

  const handleReparse = async (id: string) => {
    setReparsing(id);
    try {
      await api.admin.reparsePolicy(id);
      await loadPolicies();
    } catch (err) {
      alert(`重新解析失败: ${err}`);
    } finally {
      setReparsing(null);
    }
  };

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
          <h1 className="text-2xl font-semibold">政策管理</h1>
          <p className="text-sm text-muted-foreground">上传和管理政策文件</p>
        </div>
        <div className="flex gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.doc"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) {
                handleUpload(file);
                e.target.value = "";
              }
            }}
          />
          <Button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="gap-1.5"
          >
            {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
            上传政策文件
          </Button>
        </div>
      </div>

      <div className="flex gap-2">
        <div className="relative flex-1 max-w-sm">
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

      {loading ? (
        <div className="flex justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-20 text-muted-foreground">
          <FileText className="h-12 w-12 mx-auto mb-4 opacity-30" />
          <p>暂无政策文件</p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((policy) => (
            <Card key={policy.id} className="hover:bg-muted/30 transition-colors">
              <CardContent className="p-4 flex items-center gap-4">
                <div className="flex-shrink-0 p-2 rounded-lg bg-muted">
                  <FileText className="h-5 w-5 text-muted-foreground" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="font-medium truncate">{policy.name}</h3>
                    {statusBadge(policy.status)}
                  </div>
                  <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                    {policy.issuing_body && <span>{policy.issuing_body}</span>}
                    {policy.doc_type && <span>{policy.doc_type}</span>}
                    {policy.policy_level && <span>{policy.policy_level}</span>}
                    <span>{new Date(policy.upload_time).toLocaleDateString("zh-CN")}</span>
                  </div>
                </div>
                <div className="flex gap-1 flex-shrink-0">
                  {policy.status === "active" && (
                    <Button
                      variant="ghost"
                      size="icon"
                      title="重新解析"
                      onClick={() => handleReparse(policy.id)}
                      disabled={reparsing === policy.id}
                    >
                      <RefreshCw className={`h-4 w-4 ${reparsing === policy.id ? "animate-spin" : ""}`} />
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="icon"
                    title="删除"
                    onClick={() => setDeleteTarget(policy)}
                    className="text-destructive hover:text-destructive"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <AlertDialog open={!!deleteTarget} onOpenChange={() => setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除</AlertDialogTitle>
            <AlertDialogDescription>
              确定要删除政策「{deleteTarget?.name}」吗？此操作不可恢复。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleting ? <Loader2 className="h-4 w-4 animate-spin" /> : "删除"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
