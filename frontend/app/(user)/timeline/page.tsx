"use client";

import { useState, useEffect, useCallback } from "react";
import { api, TimelineItem } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Calendar, AlertCircle, Loader2 } from "lucide-react";
import Link from "next/link";

export default function TimelinePage() {
  const [items, setItems] = useState<TimelineItem[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.policies.timeline();
      setItems(data);
    } catch {
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const groupByMonth = (items: TimelineItem[]) => {
    const groups: Record<string, TimelineItem[]> = {};
    for (const item of items) {
      if (!item.deadline) continue;
      const date = new Date(item.deadline);
      const key = `${date.getFullYear()}年${date.getMonth() + 1}月`;
      if (!groups[key]) groups[key] = [];
      groups[key].push(item);
    }
    return Object.entries(groups).sort(([a], [b]) => a.localeCompare(b));
  };

  const isUrgent = (deadline: string) => {
    const days = Math.ceil((new Date(deadline).getTime() - Date.now()) / (1000 * 60 * 60 * 24));
    return days <= 14 && days >= 0;
  };

  const isPast = (deadline: string) => {
    return new Date(deadline) < new Date();
  };

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const grouped = groupByMonth(items);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">申报时间轴</h1>
        <p className="text-sm text-muted-foreground">追踪政策的申报截止日期</p>
      </div>

      {items.length === 0 ? (
        <div className="text-center py-20 text-muted-foreground">
          <Calendar className="h-12 w-12 mx-auto mb-4 opacity-30" />
          <p>暂无申报时间节点数据</p>
          <p className="text-sm">请等待政策解析完成</p>
        </div>
      ) : (
        <div className="space-y-8">
          {grouped.map(([month, monthItems]) => (
            <div key={month}>
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Calendar className="h-5 w-5 text-primary" />
                {month}
              </h2>
              <div className="space-y-3 border-l-2 border-primary/20 pl-6 ml-4">
                {monthItems.map((item) => (
                  <Link key={item.id} href={`/policies/${item.id}`}>
                    <Card className={`hover:shadow-md transition-shadow cursor-pointer ${isUrgent(item.deadline!) ? "border-orange-200 bg-orange-50/50" : ""} ${isPast(item.deadline!) ? "opacity-60" : ""}`}>
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex-1 min-w-0">
                            <h3 className="font-medium line-clamp-1">{item.name}</h3>
                            <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                              {item.deadline && (
                                <Badge variant={isPast(item.deadline) ? "secondary" : isUrgent(item.deadline) ? "warning" : "default"}>
                                  <AlertCircle className="h-3 w-3 mr-1" />
                                  {isPast(item.deadline) ? "已截止" : isUrgent(item.deadline) ? "即将截止" : `截止 ${item.deadline}`}
                                </Badge>
                              )}
                              {item.doc_type && <Badge variant="outline">{item.doc_type}</Badge>}
                            </div>
                            {item.issuing_body && (
                              <p className="text-xs text-muted-foreground mt-1">{item.issuing_body}</p>
                            )}
                          </div>
                          <div className="text-xs text-muted-foreground flex-shrink-0">
                            {item.effective_date && (
                              <span>生效: {item.effective_date}</span>
                            )}
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
