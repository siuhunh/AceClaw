"use client";

import Editor from "@monaco-editor/react";
import { cn } from "@/lib/utils";

type Props = {
  path: string | null;
  value: string;
  onChange: (v: string) => void;
  className?: string;
};

export function MonacoEditorPanel({ path, value, onChange, className }: Props) {
  const language = path?.endsWith(".json") ? "json" : "markdown";

  return (
    <div className={cn("flex h-full min-h-0 min-w-0 flex-1 flex-col bg-white", className)}>
      <div className="min-h-0 flex-1">
        {path ? (
          <Editor
            height="100%"
            language={language}
            theme="vs"
            value={value}
            onChange={(v) => onChange(v ?? "")}
            options={{
              minimap: { enabled: true },
              wordWrap: "on",
              fontSize: 13,
              scrollBeyondLastLine: false,
            }}
          />
        ) : (
          <div className="flex h-full items-center justify-center p-6 text-center text-sm text-slate-400">
            在左侧选择会话、记忆或技能，打开 SKILL / MEMORY 文件进行编辑。
          </div>
        )}
      </div>
    </div>
  );
}
