"use client";

import { useState, useEffect, useCallback } from "react";
import { api, User } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Loader2, User as UserIcon, Trash2, Shield } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

export default function AdminUsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleteTarget, setDeleteTarget] = useState<User | null>(null);
  const [deleting, setDeleting] = useState(false);
  const { user: currentUser } = useAuth();

  const loadUsers = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.admin.listUsers();
      setUsers(data);
    } catch {} finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  const handleUpdateRole = async (userId: string, role: string) => {
    try {
      await api.admin.updateUserRole(userId, role);
      setUsers(users.map((u) => (u.id === userId ? { ...u, role } : u)));
    } catch (err) {
      alert(`更新失败: ${err}`);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await api.admin.deleteUser(deleteTarget.id);
      setUsers(users.filter((u) => u.id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch (err) {
      alert(`删除失败: ${err}`);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">用户管理</h1>
        <p className="text-sm text-muted-foreground">管理系统用户和角色</p>
      </div>

      {loading ? (
        <div className="flex justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="space-y-2">
          {users.map((user) => (
            <Card key={user.id}>
              <CardContent className="p-4 flex items-center gap-4">
                <div className="flex-shrink-0 p-2 rounded-full bg-muted">
                  <UserIcon className="h-5 w-5 text-muted-foreground" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="font-medium">{user.username}</h3>
                    {user.id === currentUser?.id && (
                      <Badge variant="secondary">当前账号</Badge>
                    )}
                    <Badge variant={user.role === "admin" ? "default" : "outline"}>
                      {user.role === "admin" ? (
                        <><Shield className="h-3 w-3 mr-1" />管理员</>
                      ) : "普通用户"}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    注册时间：{new Date(user.created_at).toLocaleDateString("zh-CN")}
                  </p>
                </div>
                <div className="flex gap-2 flex-shrink-0">
                  {user.id !== currentUser?.id && (
                    <>
                      <Select
                        value={user.role}
                        onValueChange={(v) => handleUpdateRole(user.id, v)}
                      >
                        <SelectTrigger className="w-28">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="user">普通用户</SelectItem>
                          <SelectItem value="admin">管理员</SelectItem>
                        </SelectContent>
                      </Select>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setDeleteTarget(user)}
                        className="text-destructive hover:text-destructive"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <AlertDialog open={!!deleteTarget} onOpenChange={() => setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除用户</AlertDialogTitle>
            <AlertDialogDescription>
              确定要删除用户「{deleteTarget?.username}」吗？此操作不可恢复。
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
