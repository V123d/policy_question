"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import { api, PolicyStructured } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from "@/components/ui/accordion";
import {
  Building2, Calendar, Globe, Phone, Mail,
  Loader2, ArrowLeft, FileText, Users,
  Target, Gift, Clock, ChevronRight, Tag,
  AlertCircle, Hash, ListChecks, BookOpen,
  BarChart3, Link2, Info, CheckCircle2,
  StickyNote, Zap, ShieldCheck
} from "lucide-react";
import Link from "next/link";

// ─── Field category definitions ─────────────────────────────────────────────
type CategoryKey =
  | "basic" | "measures" | "standards" | "conditions"
  | "materials" | "timeline" | "contact" | "other";

type CategoryDef = {
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  accentClass: string;
  pillClass: string;
  fields: string[];
};

const FIELD_CATEGORIES: Record<CategoryKey, CategoryDef> = {
  basic: {
    label: "基本信息",
    icon: Info,
    accentClass: "text-blue-600 bg-blue-50 border-blue-200",
    pillClass: "bg-blue-100 text-blue-700 border-blue-200",
    fields: ["申报对象", "适用对象", "支持对象", "政策对象"],
  },
  measures: {
    label: "分项支持措施",
    icon: Gift,
    accentClass: "text-purple-600 bg-purple-50 border-purple-200",
    pillClass: "bg-purple-100 text-purple-700 border-purple-200",
    fields: ["支持方向", "支持内容", "支持措施", "支持类别", "分项支持措施", "资金支持方向"],
  },
  standards: {
    label: "补贴与奖励标准",
    icon: BarChart3,
    accentClass: "text-green-600 bg-green-50 border-green-200",
    pillClass: "bg-green-100 text-green-700 border-green-200",
    fields: ["支持标准", "补贴标准", "奖励标准", "补贴比例", "奖励比例", "支持比例", "资助标准", "奖励金额", "补贴金额", "最高奖励", "最高补贴"],
  },
  conditions: {
    label: "申报条件",
    icon: Target,
    accentClass: "text-orange-600 bg-orange-50 border-orange-200",
    pillClass: "bg-orange-100 text-orange-700 border-orange-200",
    fields: ["申报条件", "申报要求", "申报资格", "基本条件", "支持条件"],
  },
  materials: {
    label: "申报材料",
    icon: ListChecks,
    accentClass: "text-teal-600 bg-teal-50 border-teal-200",
    pillClass: "bg-teal-100 text-teal-700 border-teal-200",
    fields: ["申报材料", "申报材料清单", "材料清单", "材料要求", "提交材料", "所需材料"],
  },
  timeline: {
    label: "申报时间",
    icon: Clock,
    accentClass: "text-rose-600 bg-rose-50 border-rose-200",
    pillClass: "bg-rose-100 text-rose-700 border-rose-200",
    fields: ["申报时间", "申报截止", "申报截止日期", "申报开始", "申报期限", "申报窗口"],
  },
  contact: {
    label: "联系方式",
    icon: Phone,
    accentClass: "text-slate-600 bg-slate-50 border-slate-200",
    pillClass: "bg-slate-100 text-slate-700 border-slate-200",
    fields: ["联系方式", "联系电话", "联系人", "咨询方式", "咨询渠道"],
  },
  other: {
    label: "其他信息",
    icon: Hash,
    accentClass: "text-gray-600 bg-gray-50 border-gray-200",
    pillClass: "bg-gray-100 text-gray-700 border-gray-200",
    fields: [],
  },
};

function categorizeField(key: string): CategoryKey {
  for (const [catKey, cat] of Object.entries(FIELD_CATEGORIES) as [CategoryKey, CategoryDef][]) {
    if (cat.fields.some((f: string) => key.includes(f) || f.includes(key))) {
      return catKey;
    }
  }
  const k = key;
  if (/补贴|奖励|资助|支持金额|补贴金额|奖励金额|标准|比例|额度|最高/i.test(k)) return "standards";
  if (/条件|要求|资格/i.test(k)) return "conditions";
  if (/材料|清单|文件/i.test(k)) return "materials";
  if (/时间|截止|期限|开始|截止日期/i.test(k)) return "timeline";
  if (/联系|电话|咨询/i.test(k)) return "contact";
  if (/支持方向|支持内容|支持措施|分项/i.test(k)) return "measures";
  if (/对象|适用/i.test(k)) return "basic";
  return "other";
}

// ─── Icon map ────────────────────────────────────────────────────────────────
const FIELD_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  "申报对象": Users, "适用对象": Users, "支持对象": Users,
  "支持方向": Target, "支持内容": Gift, "支持措施": Gift,
  "支持标准": BarChart3, "补贴标准": BarChart3, "奖励标准": BarChart3,
  "申报条件": Target, "申报要求": Target, "申报材料": ListChecks,
  "申报时间": Clock, "申报截止": Clock, "联系方式": Phone,
  "联系电话": Phone, "联系人": Users, "生效日期": Calendar,
  "申报截止日期": Calendar,
};

function getFieldIcon(key: string) {
  for (const [k, Icon] of Object.entries(FIELD_ICONS)) {
    if (key.includes(k) || k.includes(key)) return Icon;
  }
  return Tag;
}

// ─── Value renderer ──────────────────────────────────────────────────────────
function FieldValueDisplay({ value }: { value: unknown }): React.ReactNode {
  if (value === null || value === undefined) {
    return <span className="text-muted-foreground text-sm italic">暂无</span>;
  }

    if (Array.isArray(value)) {
    if (value.length === 0) {
      return <span className="text-muted-foreground text-sm italic">暂无</span>;
    }
    const allSimple = value.every(v => typeof v !== "object");
    if (allSimple) {
      return (
        <div className="flex flex-wrap gap-2">
          {value.map((item, i) => (
            <Badge
              key={i}
              variant="secondary"
              className="text-xs px-2.5 py-1 rounded-md border bg-muted/70 text-foreground font-normal"
            >
              {String(item)}
            </Badge>
          ))}
        </div>
      );
    }
    // Items are objects
    return (
      <div className="space-y-2">
        {value.map((item, i) => {
          if (typeof item === "object" && item !== null) {
            const entries = Object.entries(item as Record<string, unknown>);
            const isSingleField = entries.length === 1;
            if (isSingleField) {
              const [[k, v]] = entries;
              return (
                <div key={i} className="flex items-start gap-2 py-1.5 px-3 bg-muted/40 rounded-md border border-border/40">
                  <span className="text-xs font-medium text-muted-foreground min-w-0 flex-shrink-0 mt-0.5">{k}：</span>
                  <span className="text-sm text-foreground leading-relaxed break-words">{FieldValueDisplay({ value: v })}</span>
                </div>
              );
            }
            return (
              <div key={i} className="bg-muted/40 rounded-lg p-3 border border-border/50 space-y-1.5">
                {entries.map(([k, v]) => (
                  <div key={k} className="flex gap-3">
                    <span className="text-xs font-medium text-muted-foreground min-w-0 flex-shrink-0 mt-0.5">{k}：</span>
                    <span className="text-xs text-foreground leading-relaxed break-words">{FieldValueDisplay({ value: v })}</span>
                  </div>
                ))}
              </div>
            );
          }
          return (
            <div key={i} className="flex items-center gap-2 py-1.5 px-3 bg-muted/40 rounded-md border border-border/40">
              <span className="text-xs text-foreground">{String(item)}</span>
            </div>
          );
        })}
      </div>
    );
  }

  if (typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>);
    return (
      <div className="bg-muted/30 rounded-lg p-3 border border-border/50 space-y-2">
        {entries.map(([k, v]) => (
          <div key={k} className="flex gap-3">
            <span className="text-xs font-medium text-muted-foreground min-w-0 flex-shrink-0 mt-0.5">{k}：</span>
            <span className="text-sm text-foreground leading-relaxed break-words">{FieldValueDisplay({ value: v })}</span>
          </div>
        ))}
      </div>
    );
  }

  const str = String(value);
  if (str.length > 150) {
    return (
      <div className="text-sm text-foreground leading-relaxed space-y-1">
        {str.split(/\n+/).filter(l => l.trim()).map((line, i) => (
          <p key={i} className="text-sm leading-relaxed">{line}</p>
        ))}
      </div>
    );
  }
  return <span className="text-sm text-foreground">{str}</span>;
}

// ─── Sub-policy card renderer ──────────────────────────────────────────────────
function SubPolicyCard({ item }: { item: Record<string, unknown> }) {
  const entries = Object.entries(item).filter(([, v]) => v !== null && v !== undefined && v !== "");
  if (entries.length === 0) return null;
  return (
    <div className="bg-muted/20 rounded-xl border border-border/50 p-4 space-y-2">
      {entries.map(([k, v]) => {
        const isMainField = ["子政策名称", "支持内容"].includes(k);
        return (
          <div key={k} className="flex gap-3">
            <span className={`min-w-0 flex-shrink-0 mt-0.5 ${isMainField ? "text-xs font-semibold text-foreground" : "text-xs font-medium text-muted-foreground"}`}>
              {k}：
            </span>
            <span className={`text-xs leading-relaxed break-words ${isMainField ? "text-foreground" : "text-muted-foreground"}`}>
              {FieldValueDisplay({ value: v })}
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ─── Field row inside a category section ───────────────────────────────────
function FieldRow({ label, value }: { label: string; value: unknown }) {
  const Icon = getFieldIcon(label);

  // Special rendering for sub-policy list
  if (
    label === "分项支持措施" &&
    Array.isArray(value) &&
    value.length > 0 &&
    value.every(v => typeof v === "object" && v !== null)
  ) {
    return (
      <div className="py-3">
        <p className="text-sm font-medium text-foreground mb-2">{label}</p>
        <div className="space-y-3">
          {(value as Record<string, unknown>[]).map((item, i) => (
            <SubPolicyCard key={i} item={item} />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-3 py-3 first:pt-0 last:pb-0 border-b border-border/30 last:border-0">
      <div className="flex-shrink-0 mt-1">
        <Icon className="h-4 w-4 text-muted-foreground" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-foreground mb-1.5">{label}</p>
        <FieldValueDisplay value={value} />
      </div>
    </div>
  );
}

// ─── Summary stats bar ──────────────────────────────────────────────────────
function StatsBar({ grouped, total }: { grouped: Record<CategoryKey, number>; total: number }) {
  return (
    <div className="flex flex-wrap gap-2 mb-6">
      <div className="flex items-center gap-1.5 px-3 py-1.5 bg-primary/5 border border-primary/20 rounded-full text-xs font-medium text-primary">
        <Zap className="h-3 w-3" />
        共 {total} 个字段
      </div>
      {Object.entries(grouped).map(([key, count]) => {
        if (count === 0) return null;
        const cat = FIELD_CATEGORIES[key as CategoryKey];
        const CatIcon = cat.icon;
        return (
          <div
            key={key}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border ${cat.pillClass}`}
          >
            <CatIcon className="h-3 w-3" />
            {cat.label} {count}
          </div>
        );
      })}
    </div>
  );
}

// ─── Deadline alert ──────────────────────────────────────────────────────────
function DeadlineAlert({ deadline }: { deadline: string }) {
  const now = new Date();
  const dl = new Date(deadline);
  const diffDays = Math.ceil((dl.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));

  if (diffDays < 0) return null;

  let alertClass = "bg-green-50 border-green-200 text-green-700";
  let alertIcon: React.ComponentType<{ className?: string }> = CheckCircle2;
  let alertText = "申报进行中";

  if (diffDays <= 3) {
    alertClass = "bg-red-50 border-red-200 text-red-700";
    alertIcon = AlertCircle;
    alertText = `距截止仅剩 ${diffDays} 天`;
  } else if (diffDays <= 14) {
    alertClass = "bg-orange-50 border-orange-200 text-orange-700";
    alertIcon = Clock;
    alertText = `距截止 ${diffDays} 天`;
  }

  const AlertIcon = alertIcon;
  return (
    <div className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-xs font-medium ${alertClass}`}>
      <AlertIcon className="h-3.5 w-3.5" />
      {alertText}（{deadline}）
    </div>
  );
}

// ─── Main structured data section ─────────────────────────────────────────
function StructuredDataSection({ data }: { data: Record<string, unknown> }) {
  const entries = Object.entries(data).filter(
    ([, v]) => v !== null && v !== undefined && v !== ""
  );

  if (entries.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center mb-4">
          <Info className="h-8 w-8 text-muted-foreground" />
        </div>
        <p className="text-muted-foreground font-medium">暂无结构化数据</p>
        <p className="text-xs text-muted-foreground mt-1">该政策文档尚未完成结构化解析</p>
      </div>
    );
  }

  // Group entries by category
  const grouped: Record<CategoryKey, [string, unknown][]> = {
    basic: [], measures: [], standards: [], conditions: [],
    materials: [], timeline: [], contact: [], other: [],
  };
  for (const [key, value] of entries) {
    const cat = categorizeField(key);
    grouped[cat].push([key, value]);
  }

  const renderOrder: CategoryKey[] = ["basic", "measures", "standards", "conditions", "materials", "timeline", "contact", "other"];
  const counts = Object.fromEntries(
    renderOrder.map(k => [k, grouped[k].length])
  ) as Record<CategoryKey, number>;
  const totalFields = entries.length;

  return (
    <div>
      <StatsBar grouped={counts} total={totalFields} />

      <Accordion type="multiple" defaultValue={renderOrder} className="space-y-2">
        {renderOrder.map(catKey => {
          const items = grouped[catKey];
          if (items.length === 0) return null;
          const cat = FIELD_CATEGORIES[catKey];
          const CatIcon = cat.icon;
          const [bgClass, textClass] = cat.accentClass.split(" ");

          return (
            <AccordionItem
              key={catKey}
              value={catKey}
              className="border border-border/60 rounded-xl bg-card overflow-hidden shadow-sm"
            >
              <AccordionTrigger className="px-5 py-3.5 hover:no-underline hover:bg-muted/20 px-5">
                <div className="flex items-center gap-3">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${bgClass}`}>
                    <CatIcon className={`h-4 w-4 ${textClass}`} />
                  </div>
                  <span className="text-sm font-semibold text-foreground">{cat.label}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${cat.pillClass}`}>
                    {items.length}
                  </span>
                </div>
              </AccordionTrigger>
              <AccordionContent>
                <div className="px-5 pb-4">
                  <div className="bg-muted/20 rounded-xl border border-border/40 divide-y divide-border/30">
                    {items.map(([label, value]) => (
                      <FieldRow key={label} label={label} value={value} />
                    ))}
                  </div>
                </div>
              </AccordionContent>
            </AccordionItem>
          );
        })}
      </Accordion>
    </div>
  );
}

// ─── Meta info cards ─────────────────────────────────────────────────────────
function MetaCards({ policy }: { policy: PolicyStructured }) {
  const cards = [
    policy.issuing_body && {
      icon: Building2, label: "发文单位", value: policy.issuing_body,
    },
    policy.effective_date && {
      icon: Calendar, label: "生效日期", value: policy.effective_date,
    },
    policy.deadline && {
      icon: Clock, label: "申报截止", value: policy.deadline,
    },
    (policy.consultation.phone || policy.consultation.contact) && {
      icon: Phone, label: "联系方式",
      value: policy.consultation.phone || policy.consultation.contact || "",
    },
    policy.consultation.website && {
      icon: Globe, label: "咨询网站", value: policy.consultation.website,
    },
    (policy.consultation.contact && policy.consultation.phone) && {
      icon: Users, label: "联系人", value: policy.consultation.contact,
    },
  ].filter(Boolean) as { icon: React.ComponentType<{ className?: string }>; label: string; value: string }[];

  if (cards.length === 0) return null;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
      {cards.map((card, i) => {
        const Icon = card.icon;
        return (
          <div
            key={i}
            className="flex items-center gap-3 px-4 py-3 bg-card border border-border/60 rounded-xl shadow-sm hover:shadow-md hover:border-border transition-all duration-200"
          >
            <div className="w-10 h-10 rounded-xl bg-primary/8 flex items-center justify-center flex-shrink-0">
              <Icon className="h-4.5 w-4.5 text-primary" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-xs text-muted-foreground font-medium leading-tight">{card.label}</p>
              <p className="text-sm font-semibold text-foreground truncate mt-0.5">{card.value}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── Level badge ─────────────────────────────────────────────────────────────
function LevelBadge({ level }: { level?: string | null }) {
  if (!level) return null;
  const colors: Record<string, string> = {
    "国家级": "bg-red-50 text-red-700 border-red-200",
    "省级": "bg-orange-50 text-orange-700 border-orange-200",
    "市级": "bg-blue-50 text-blue-700 border-blue-200",
    "区级": "bg-green-50 text-green-700 border-green-200",
  };
  const cls = colors[level] || "bg-gray-50 text-gray-700 border-gray-200";
  return (
    <Badge className={`${cls} border text-xs font-medium px-2.5 py-1 rounded-full`}>
      {level}
    </Badge>
  );
}

// ─── Main page ──────────────────────────────────────────────────────────────
export default function PolicyDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [policy, setPolicy] = useState<PolicyStructured | null>(null);
  const [rawText, setRawText] = useState<string>("");
  const [loading, setLoading] = useState(true);

  const loadPolicy = useCallback(async () => {
    setLoading(true);
    try {
      const [structured, text] = await Promise.all([
        api.policies.getStructured(id),
        api.policies.get(id).then((p) => p.raw_text || ""),
      ]);
      setPolicy(structured);
      setRawText(text);
    } catch {
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadPolicy();
  }, [loadPolicy]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="text-sm text-muted-foreground">加载政策信息中...</p>
      </div>
    );
  }

  if (!policy) {
    return (
      <div className="text-center py-20">
        <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center mx-auto mb-4">
          <AlertCircle className="h-8 w-8 text-muted-foreground" />
        </div>
        <p className="text-muted-foreground font-medium">政策不存在</p>
        <Link href="/policies">
          <Button variant="ghost" className="mt-2">返回政策库</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-1 space-y-5">
      {/* ── Header ── */}
      <div className="flex items-start gap-3">
        <Link href="/policies">
          <Button variant="ghost" size="icon" className="mt-0.5 flex-shrink-0">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div className="flex-1 min-w-0">
          <div className="flex items-start gap-2 flex-wrap">
            <h1 className="text-xl md:text-2xl font-bold text-foreground leading-tight">{policy.name}</h1>
          </div>
          <div className="flex gap-1.5 mt-2 flex-wrap items-center">
            {policy.doc_type && (
              <Badge variant="outline" className="text-xs rounded-full">{policy.doc_type}</Badge>
            )}
            <LevelBadge level={policy.policy_level} />
            {policy.policy_subject && (
              <Badge variant="outline" className="text-xs bg-muted/50 rounded-full">{policy.policy_subject}</Badge>
            )}
          </div>
        </div>
      </div>

      {/* ── Meta cards ── */}
      <MetaCards policy={policy} />

      {/* ── Deadline alert ── */}
      {policy.deadline && <DeadlineAlert deadline={policy.deadline} />}

      {/* ── Tabs ── */}
      <Tabs defaultValue="structured" className="w-full">
        <TabsList className="mb-4">
          <TabsTrigger value="structured" className="gap-1.5">
            <BookOpen className="h-3.5 w-3.5" />
            结构化信息
          </TabsTrigger>
          <TabsTrigger value="raw" className="gap-1.5">
            <FileText className="h-3.5 w-3.5" />
            原始全文
          </TabsTrigger>
        </TabsList>

        <TabsContent value="structured">
          <StructuredDataSection data={policy.structured_data} />
        </TabsContent>

        <TabsContent value="raw">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <FileText className="h-4 w-4 text-muted-foreground" />
                原始政策全文
              </CardTitle>
            </CardHeader>
            <CardContent>
              {rawText ? (
                <div className="bg-muted/40 rounded-xl p-5 border border-border/60">
                  <pre className="text-sm whitespace-pre-wrap text-foreground leading-relaxed font-mono overflow-x-auto max-h-[600px] overflow-y-auto scrollbar-thin">
                    {rawText}
                  </pre>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <FileText className="h-10 w-10 text-muted-foreground mb-3" />
                  <p className="text-muted-foreground text-sm">暂无原文内容</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
