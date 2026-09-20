"use client";

import React, { useState, useRef, useEffect } from "react";
import { X, Send, Sparkles, Bot, User, CornerDownLeft } from "lucide-react";

interface AiCopilotDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

interface Message {
  id: string;
  sender: "user" | "copilot";
  text: string;
  time: string;
}

export function AiCopilotDrawer({ isOpen, onClose }: AiCopilotDrawerProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      sender: "copilot",
      text: "Hello! I am your **KOHLER Facility Copilot**. I have real-time access to the Terminal 2 sensor database, active tickets, and baseline models. How can I assist you with restroom operations today?",
      time: "Just now",
    },
  ]);
  const [inputText, setInputText] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const quickPrompts = [
    "Which fixture has the worst water waste right now?",
    "Summarize overnight leaks in Restroom A",
    "What is the total utility cost impact?",
    "Recommend maintenance priority order",
  ];

  const handleSend = async (queryText?: string) => {
    const textToSend = queryText || inputText;
    if (!textToSend.trim() || loading) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      sender: "user",
      text: textToSend.trim(),
      time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputText("");
    setLoading(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: textToSend }),
      });

      if (!res.ok) throw new Error("Failed to get response");
      const data = await res.json();

      const copilotMsg: Message = {
        id: (Date.now() + 1).toString(),
        sender: "copilot",
        text: data.reply || "I analyzed the current telemetry. No additional concerns detected.",
        time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, copilotMsg]);
    } catch (err) {
      console.error("AI Copilot request error:", err);
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          sender: "copilot",
          text: "I encountered an error connecting to the telemetry service. Please check your backend connection.",
          time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  // Simple formatter for **bold** text in assistant responses
  const renderFormattedText = (text: string) => {
    const parts = text.split(/(\*\*.*?\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return (
          <strong key={i} className="text-[#D4A359] font-semibold">
            {part.slice(2, -2)}
          </strong>
        );
      }
      return part;
    });
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Dimmed backdrop */}
      <div
        onClick={onClose}
        className="absolute inset-0 bg-black/60 backdrop-blur-sm transition-opacity"
      />

      {/* Slide-over Drawer Panel */}
      <div className="absolute inset-y-0 right-0 max-w-full flex pl-10">
        <div className="w-screen max-w-md bg-[#0F141D] border-l border-white/10 shadow-2xl flex flex-col">
          {/* Drawer Header */}
          <div className="px-5 py-4 border-b border-white/[0.08] flex items-center justify-between bg-[#10141A]/90">
            <div className="flex items-center gap-2.5">
              <div className="h-7 w-7 rounded-lg bg-[#D4A359]/15 border border-[#D4A359]/30 flex items-center justify-center text-[#D4A359]">
                <Sparkles className="h-4 w-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-[#F0F6FC] tracking-wide">
                  AI Facility Copilot
                </h3>
                <p className="text-[11px] text-[#8B949E]">Google Gemini with SQLite Telemetry</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-[#8B949E] hover:text-[#F0F6FC] hover:bg-white/10 transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* Quick Prompts */}
          <div className="px-4 py-2.5 bg-[#0B0F14] border-b border-white/[0.06] overflow-x-auto flex gap-2 no-scrollbar">
            {quickPrompts.map((qp, idx) => (
              <button
                key={idx}
                onClick={() => handleSend(qp)}
                className="whitespace-nowrap px-2.5 py-1 rounded-full text-[11px] bg-white/[0.04] hover:bg-white/[0.1] text-[#C9D1D9] hover:text-[#F0F6FC] border border-white/[0.08] transition-all shrink-0"
              >
                {qp}
              </button>
            ))}
          </div>

          {/* Chat Messages */}
          <div className="flex-1 p-4 overflow-y-auto space-y-4">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-3 ${msg.sender === "user" ? "justify-end" : "justify-start"}`}
              >
                {msg.sender === "copilot" && (
                  <div className="h-7 w-7 rounded-full bg-[#4D88C7]/20 border border-[#4D88C7]/40 flex items-center justify-center text-[#4D88C7] shrink-0 mt-0.5">
                    <Bot className="h-3.5 w-3.5" />
                  </div>
                )}
                <div
                  className={`max-w-[85%] rounded-md px-3.5 py-2.5 text-xs leading-relaxed ${
                    msg.sender === "user"
                      ? "bg-[#4D88C7] text-white rounded-br-none"
                      : "bg-[#1B222C] text-[#C9D1D9] border border-white/[0.08] rounded-bl-none"
                  }`}
                >
                  <p className="whitespace-pre-line">{renderFormattedText(msg.text)}</p>
                  <span className="text-[10px] text-white/60 block text-right mt-1 font-mono">
                    {msg.time}
                  </span>
                </div>
                {msg.sender === "user" && (
                  <div className="h-7 w-7 rounded-full bg-white/10 border border-white/20 flex items-center justify-center text-white shrink-0 mt-0.5">
                    <User className="h-3.5 w-3.5" />
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div className="flex gap-3 justify-start items-center text-xs text-[#8B949E]">
                <div className="h-7 w-7 rounded-full bg-[#4D88C7]/20 border border-[#4D88C7]/40 flex items-center justify-center text-[#4D88C7] shrink-0">
                  <Bot className="h-3.5 w-3.5 animate-spin" />
                </div>
                <div className="bg-[#1B222C] rounded-md px-3.5 py-2">
                  <span className="inline-flex gap-1 items-center">
                    <span className="h-1.5 w-1.5 rounded-full bg-[#D4A359] animate-bounce" />
                    <span className="h-1.5 w-1.5 rounded-full bg-[#D4A359] animate-bounce [animation-delay:0.2s]" />
                    <span className="h-1.5 w-1.5 rounded-full bg-[#D4A359] animate-bounce [animation-delay:0.4s]" />
                  </span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Chat Input Bar */}
          <div className="p-3 border-t border-white/[0.08] bg-[#10141A]">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSend();
              }}
              className="flex items-center gap-2 bg-[#0B0F14] border border-white/15 rounded-lg px-3 py-1.5 focus-within:border-[#D4A359] transition-all"
            >
              <input
                type="text"
                placeholder="Ask about water waste, leaks, or tickets..."
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                className="flex-1 bg-transparent text-xs text-[#F0F6FC] placeholder-[#8B949E] focus:outline-none"
              />
              <button
                type="submit"
                disabled={!inputText.trim() || loading}
                className="p-1.5 rounded bg-[#D4A359] hover:bg-[#D4A359]/90 disabled:opacity-30 text-black transition-all"
              >
                <Send className="h-3 w-3" />
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
