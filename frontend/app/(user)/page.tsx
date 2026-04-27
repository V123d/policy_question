"use client";

import Link from "next/link";
import { MessageSquare, BookOpen, Calendar, ArrowRight, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const features = [
  {
    icon: MessageSquare,
    title: "智能问答",
    description: "基于大模型理解政策文件，精准回答各类申报问题",
    href: "/chat",
    color: "text-blue-600 bg-blue-50",
  },
  {
    icon: BookOpen,
    title: "政策库",
    description: "浏览所有已解析的政策文件，查看完整的结构化信息",
    href: "/policies",
    color: "text-green-600 bg-green-50",
  },
  {
    icon: Calendar,
    title: "申报时间轴",
    description: "追踪政策申报的时间节点，再也不会错过截止日期",
    href: "/timeline",
    color: "text-orange-600 bg-orange-50",
  },
];

export default function HomePage() {
  return (
    <div className="flex flex-col">
      <section className="py-20 text-center">
        <div className="container">
          <div className="flex justify-center mb-6">
            <div className="p-4 rounded-2xl bg-primary/10">
              <Shield className="h-12 w-12 text-primary" />
            </div>
          </div>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-4">
            政策问答智能体
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto mb-8">
            基于大模型的智能政策解读助手，自动解析政策文件结构，
            <br />
            让企业申报不再迷茫
          </p>
          <div className="flex gap-4 justify-center">
            <Link href="/chat">
              <Button size="lg" className="gap-2">
                开始咨询 <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <Link href="/policies">
              <Button variant="outline" size="lg">
                浏览政策库
              </Button>
            </Link>
          </div>
        </div>
      </section>

      <section className="py-16 bg-muted/30">
        <div className="container">
          <h2 className="text-2xl font-semibold text-center mb-10">核心功能</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {features.map((feature) => (
              <Link key={feature.href} href={feature.href}>
                <Card className="h-full hover:shadow-md transition-shadow cursor-pointer">
                  <CardHeader>
                    <div className={`p-2 rounded-lg w-fit ${feature.color}`}>
                      <feature.icon className="h-6 w-6" />
                    </div>
                    <CardTitle className="mt-4">{feature.title}</CardTitle>
                    <CardDescription>{feature.description}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <span className="text-sm text-primary flex items-center gap-1">
                      前往 <ArrowRight className="h-3 w-3" />
                    </span>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section className="py-16">
        <div className="container">
          <h2 className="text-2xl font-semibold text-center mb-10">常见问题</h2>
          <div className="max-w-3xl mx-auto space-y-4">
            {[
              {
                q: "这个系统能回答哪些类型的问题？",
                a: "系统可以回答关于政策申报对象、申报条件、申报材料、支持标准、时间节点等各类政策相关问题。",
              },
              {
                q: "政策数据是如何保证准确性的？",
                a: "每份政策文件都由大模型进行深度解析，提取结构化数据存储。用户提问时，系统直接从结构化数据中检索答案，而非依赖向量检索。",
              },
              {
                q: "如何上传新的政策文件？",
                a: "政策文件需要由管理员上传。如果您是管理员，请登录后进入管理后台进行操作。",
              },
            ].map((item, i) => (
              <Card key={i}>
                <CardContent className="pt-6">
                  <h3 className="font-medium mb-2">{item.q}</h3>
                  <p className="text-sm text-muted-foreground">{item.a}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
