"use client";

import { useState, useEffect, useCallback } from "react";
import { api, ChatLog } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Loader2, MessageSquare, Clock, Cpu } from "lucide-react";

export default function AdminQueriesPage() {
  const [logs, setLogs] = useState<ChatLog[]>([]);
  const [loading, setLoading] = useState(true);

  const loadLogs = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.admin.listQueries({ limit: 100 });
      setLogs(data);
    } catch {} finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadLogs();
  }, [loadLogs]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">问答日志</h1>
        <p className="text-sm text-muted-foreground">查看所有用户的问答记录</p>
      </div>

      {loading ? (
        <div className="flex justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : logs.length === 0 ? (
        <div className="text-center py-20 text-muted-foreground">
          <MessageSquare className="h-12 w-12 mx-auto mb-4 opacity-30" />
          <p>暂无问答记录</p>
        </div>
      ) : (
        <div className="space-y-3">
          {logs.map((log) => (
            <Card key={log.id}>
              <CardContent className="p-4 space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant="outline" className="text-xs">
                        <MessageSquare className="h-3 w-3 mr-1" />
                        {log.model_provider || "unknown"} / {log.model_name || "unknown"}
                      </Badge>
                      <Badge variant="outline" className="text-xs">
                        <Clock className="h-3 w-3 mr-1" />
                        {log.response_time_ms ? `${(log.response_time_ms / 1000).toFixed(1)}s` : "-"}
                      </Badge>
                      {log.tokens_used && (
                        <Badge variant="outline" className="text-xs">
                          <Cpu className="h-3 w-3 mr-1" />
                          {log.tokens_used} tokens
                        </Badge>
                      )}
                    </div>
                    <p className="text-sm font-medium mb-1">Q: {log.question}</p>
                    {log.answer && (
                      <p className="text-sm text-muted-foreground">
                        A: {log.answer.slice(0, 200)}{log.answer.length > 200 ? "..." : ""}
                      </p>
                    )}
                  </div>
                  <div className="text-xs text-muted-foreground flex-shrink-0">
                    {new Date(log.created_at).toLocaleString("zh-CN")}
                  </div>
                </div>
                {log.cited_policies && log.cited_policies.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    <span className="text-xs text-muted-foreground">引用政策：</span>
                    {log.cited_policies.map((p, i) => (
                      <Badge key={i} variant="secondary" className="text-xs">
                        {p.policy_name}
                      </Badge>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
