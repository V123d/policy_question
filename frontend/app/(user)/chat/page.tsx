"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useAuth } from "@/context/AuthContext";
import { api, ChatHistoryItem, Session, CitedPolicy } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { MessageSquare, Send, Plus, Trash2, Loader2, Bot, User, FileText } from "lucide-react";
import { useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

function MarkdownContent({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        table: ({ children }) => (
          <div className="w-full overflow-x-auto my-2">
            <table className="min-w-full text-xs border-collapse">{children}</table>
          </div>
        ),
        thead: ({ children }) => (
          <thead className="bg-muted/60">{children}</thead>
        ),
        th: ({ children }) => (
          <th className="px-2 py-1.5 text-left font-semibold text-foreground border border-border/50 whitespace-nowrap">{children}</th>
        ),
        td: ({ children }) => (
          <td className="px-2 py-1.5 border border-border/50 align-top text-muted-foreground">{children}</td>
        ),
        tr: ({ children }) => (
          <tr className="even:bg-muted/20">{children}</tr>
        ),
        blockquote: ({ children }) => (
          <blockquote className="border-l-3 border-primary/40 pl-3 my-1 text-muted-foreground italic">{children}</blockquote>
        ),
        code: ({ children, className }) => {
          const isBlock = className?.startsWith("language-");
          return isBlock ? (
            <code className="block bg-muted rounded p-2 text-xs overflow-x-auto my-1">{children}</code>
          ) : (
            <code className="bg-muted/70 px-1 py-0.5 rounded text-xs font-mono">{children}</code>
          );
        },
        a: ({ href, children }) => (
          <a href={href} target="_blank" rel="noopener noreferrer" className="text-primary underline">{children}</a>
        ),
        p: ({ children }) => <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>,
        ul: ({ children }) => <ul className="list-disc pl-4 space-y-0.5">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal pl-4 space-y-0.5">{children}</ol>,
        li: ({ children }) => <li className="leading-relaxed">{children}</li>,
        h1: ({ children }) => <h1 className="text-base font-bold mt-3 mb-1">{children}</h1>,
        h2: ({ children }) => <h2 className="text-sm font-bold mt-3 mb-1">{children}</h2>,
        h3: ({ children }) => <h3 className="text-sm font-semibold mt-2 mb-1">{children}</h3>,
        strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
        em: ({ children }) => <em className="italic">{children}</em>,
        hr: () => <hr className="my-3 border-border/50" />,
      }}
    >
      {content}
    </ReactMarkdown>
  );
}

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  cited?: CitedPolicy[];
};

const EXAMPLE_QUESTIONS = [
  "中小企业可以申请哪些补贴政策？",
  "专精特新企业的申报条件是什么？",
  "2024年度研发费用加计扣除怎么申请？",
];

export default function ChatPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [modelProvider, setModelProvider] = useState<string>("dashscope");
  const [stopController, setStopController] = useState<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const loadSessions = useCallback(async () => {
    try {
      const s = await api.chat.listSessions();
      setSessions(s);
    } catch (e) {
      console.error("[loadSessions] failed:", e);
      const msg = e instanceof Error ? e.message : String(e);
      if (msg.includes("Unauthorized") || msg.includes("401") || msg.includes("Token")) {
        setSessions([]);
      }
    }
  }, []);

  const loadHistory = useCallback(async (sessionId: string) => {
    try {
      const history = await api.chat.getHistory(sessionId);
      const msgs: Message[] = [];
      for (const item of history) {
        msgs.push({ id: `${item.id}-q`, role: "user", content: item.question });
        if (item.answer) {
          msgs.push({ id: `${item.id}-a`, role: "assistant", content: item.answer, cited: item.cited_policies });
        }
      }
      setMessages(msgs);
    } catch (e) {
      console.error("[loadHistory] failed:", e);
      setMessages([]);
    }
  }, []);

  useEffect(() => {
    if (user) {
      loadSessions();
    }
  }, [user, loadSessions]);

  useEffect(() => {
    if (currentSessionId) {
      loadHistory(currentSessionId);
    } else {
      setMessages([]);
    }
  }, [currentSessionId, loadHistory]);

  const handleNewSession = () => {
    setCurrentSessionId(null);
    setMessages([]);
  };

  const handleSelectSession = (sessionId: string) => {
    setCurrentSessionId(sessionId);
  };

  const handleDeleteSession = async (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    try {
      await api.chat.deleteSession(sessionId);
      setSessions(sessions.filter((s) => s.id !== sessionId));
      if (currentSessionId === sessionId) {
        setCurrentSessionId(null);
        setMessages([]);
      }
    } catch {}
  };

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const question = input.trim();
    setInput("");
    const userMsgId = Date.now().toString();
    setMessages((prev) => [...prev, { id: userMsgId, role: "user", content: question }]);
    setLoading(true);

    let assistantContent = "";
    let cited: CitedPolicy[] = [];
    const assistantMsgId = (Date.now() + 1).toString();
    const controller = new AbortController();
    setStopController(controller);

    try {
      const newSessionId = await api.chat.askStream(
        question,
        (delta) => {
          assistantContent += delta;
          setMessages((prev) => {
            const existing = prev.find((m) => m.id === assistantMsgId);
            if (existing) {
              return prev.map((m) =>
                m.id === assistantMsgId ? { ...m, content: assistantContent } : m
              );
            }
            return [...prev, { id: assistantMsgId, role: "assistant", content: delta }];
          });
        },
        currentSessionId || undefined,
        modelProvider,
        (citedPolicies) => {
          cited = citedPolicies;
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsgId ? { ...m, cited } : m
            )
          );
        },
        controller
      );

      if (newSessionId && !currentSessionId) {
        setCurrentSessionId(newSessionId);
      }

      await loadSessions();
    } catch (err) {
      if ((err as Error).name === "AbortError") {
        // User stopped - save the partial answer
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId ? { ...m, cited: [] } : m
          )
        );
      } else {
        setMessages((prev) => [
          ...prev,
          { id: (Date.now() + 2).toString(), role: "assistant", content: "抱歉，发生了错误，请稍后再试。" },
        ]);
      }
    } finally {
      setLoading(false);
      setStopController(null);
    }
  };

  const handleStop = () => {
    if (stopController) {
      stopController.abort();
    }
  };

  const handleExample = (q: string) => {
    setInput(q);
    inputRef.current?.focus();
  };

  return (
    <div className="flex h-[calc(100vh-8rem)] gap-4">
      <aside className="w-64 flex-shrink-0 flex flex-col border rounded-lg overflow-hidden">
        <div className="p-3 border-b bg-muted/30">
          <Button onClick={handleNewSession} variant="outline" size="sm" className="w-full gap-1.5">
            <Plus className="h-4 w-4" /> 新建会话
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto scrollbar-thin">
          {!user ? (
            <div className="p-4 text-sm text-muted-foreground text-center">
              <p className="mb-2">请先登录以查看对话记录</p>
              <Button variant="outline" size="sm" onClick={() => router.push("/login")}>
                登录
              </Button>
            </div>
          ) : sessions.length === 0 ? (
            <div className="p-4 text-sm text-muted-foreground text-center">
              暂无会话记录
            </div>
          ) : (
            sessions.map((session) => (
              <div
                key={session.id}
                onClick={() => handleSelectSession(session.id)}
                className={`group p-3 border-b cursor-pointer hover:bg-muted/50 transition-colors ${
                  currentSessionId === session.id ? "bg-muted" : ""
                }`}
              >
                <div className="flex items-start justify-between gap-1">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{session.name || "新会话"}</p>
                    <p className="text-xs text-muted-foreground truncate">
                      {new Date(session.updated_at).toLocaleDateString("zh-CN")}
                    </p>
                  </div>
                  <button
                    onClick={(e) => handleDeleteSession(e, session.id)}
                    className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive transition-opacity"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </aside>

      <div className="flex-1 flex flex-col border rounded-lg overflow-hidden">
        <div className="flex-1 overflow-y-auto scrollbar-thin p-4 space-y-4">
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-center space-y-6">
              <div className="p-4 rounded-full bg-primary/10">
                <Bot className="h-12 w-12 text-primary" />
              </div>
              <div>
                <h2 className="text-xl font-semibold mb-2">有什么可以帮您的？</h2>
                <p className="text-muted-foreground text-sm">
                  可以询问政策申报条件、补贴标准、申报材料等问题
                </p>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-2 max-w-2xl w-full px-4">
                {EXAMPLE_QUESTIONS.map((q) => (
                  <button
                    key={q}
                    onClick={() => handleExample(q)}
                    className="text-left text-sm p-3 rounded-lg border bg-background hover:bg-muted/50 transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <div key={msg.id} className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              {msg.role === "assistant" && (
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                  <Bot className="h-4 w-4 text-primary" />
                </div>
              )}
              <div
                className={`max-w-[70%] rounded-lg px-4 py-3 ${
                  msg.role === "user"
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted"
                }`}
              >
                <MarkdownContent content={msg.content} />
                {msg.cited && msg.cited.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-border/50">
                    <p className="text-xs opacity-70 mb-1">参考政策：</p>
                    <div className="flex flex-wrap gap-1">
                      {msg.cited.map((p, i) => (
                        <Badge key={i} variant="outline" className="text-xs">
                          <FileText className="h-3 w-3 mr-1" />
                          {p.policy_name}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              {msg.role === "user" && (
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
                  <User className="h-4 w-4" />
                </div>
              )}
            </div>
          ))}

          {loading && messages[messages.length - 1]?.role !== "assistant" && (
            <div className="flex gap-3 justify-start">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                <Bot className="h-4 w-4 text-primary" />
              </div>
              <div className="bg-muted rounded-lg px-4 py-3 flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin text-sm text-muted-foreground" />
                <span className="text-sm text-muted-foreground">正在思考...</span>
                <button
                  onClick={handleStop}
                  className="ml-2 px-2 py-0.5 text-xs rounded border border-border hover:bg-destructive/10 hover:border-destructive/30 hover:text-destructive transition-colors"
                >
                  停止
                </button>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div className="border-t p-4 bg-background">
          <div className="flex items-center gap-2 mb-2">
            <Select value={modelProvider} onValueChange={setModelProvider}>
              <SelectTrigger className="w-40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="dashscope">通义千问</SelectItem>
                <SelectItem value="openai">OpenAI GPT</SelectItem>
                <SelectItem value="qianfan">百度千帆</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex gap-2">
            <Textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="输入您的问题，按 Enter 发送..."
              className="min-h-[44px] max-h-[120px] resize-none"
              rows={1}
            />
            <Button
              onClick={loading ? handleStop : handleSend}
              disabled={!loading && !input.trim()}
              size="icon"
              className="h-[44px] w-[44px]"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground mt-1.5">
            按 Enter 发送，Shift + Enter 换行
          </p>
        </div>
      </div>
    </div>
  );
}
