"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Loader2, Tags } from "lucide-react";

export default function AdminFieldLibraryPage() {
  const [fieldMap, setFieldMap] = useState<Record<string, { label: string; count: number }>>({});
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const policies = await api.policies.list({ limit: 200 });
      const fieldCount: Record<string, { label: string; count: number }> = {};
      for (const policy of policies) {
        if (!policy.structured_data) continue;
        for (const key of Object.keys(policy.structured_data)) {
          if (!fieldCount[key]) {
            fieldCount[key] = { label: key, count: 0 };
          }
          fieldCount[key].count++;
        }
      }
      setFieldMap(fieldCount);
    } catch {} finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const fields = Object.values(fieldMap).sort((a, b) => b.count - a.count);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">字段定义库</h1>
        <p className="text-sm text-muted-foreground">
          所有政策中用到的结构化字段，共 {fields.length} 种
        </p>
      </div>

      {fields.length === 0 ? (
        <div className="text-center py-20 text-muted-foreground">
          <Tags className="h-12 w-12 mx-auto mb-4 opacity-30" />
          <p>暂无字段数据</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {fields.map((field) => (
            <Card key={field.label}>
              <CardContent className="p-4 flex items-center justify-between">
                <span className="font-medium text-sm">{field.label}</span>
                <Badge variant="secondary">
                  {field.count} 个政策使用
                </Badge>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
