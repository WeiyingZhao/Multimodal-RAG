import { Button } from "./ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Settings, HelpCircle } from "lucide-react";

interface TopBarProps {
  knowledgeBase: string;
  model: string;
  onKnowledgeBaseChange: (value: string) => void;
  onModelChange: (value: string) => void;
  onSettings: () => void;
  onHelp: () => void;
}

export function TopBar({ knowledgeBase, model, onKnowledgeBaseChange, onModelChange, onSettings, onHelp }: TopBarProps) {
  return (
    <div className="h-12 bg-background border-b border-border flex items-center justify-between px-6">
      {/* Left brand logo */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-lg flex items-center justify-center">
          <span className="text-white text-sm font-medium">RAG</span>
        </div>
        <h1 className="text-foreground">Multimodal RAG Workbench</h1>
      </div>

      {/* Center dropdown selectors */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <label className="text-sm text-muted-foreground">Knowledge Base</label>
          <Select value={knowledgeBase} onValueChange={onKnowledgeBaseChange}>
            <SelectTrigger className="w-[180px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="default">Default</SelectItem>
              <SelectItem value="tech">Technical Docs</SelectItem>
              <SelectItem value="legal">Legal Documents</SelectItem>
              <SelectItem value="medical">Medical Materials</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-sm text-muted-foreground">Model</label>
          <Select value={model} onValueChange={onModelChange}>
            <SelectTrigger className="w-[180px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="gpt-4">GPT-4</SelectItem>
              <SelectItem value="claude">Claude 3.5</SelectItem>
              <SelectItem value="gemini">Gemini Pro</SelectItem>
              <SelectItem value="qwen">Qwen</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Right icon buttons */}
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={onSettings}
          className="w-8 h-8 p-0 hover:bg-accent"
        >
          <Settings className="w-4 h-4" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={onHelp}
          className="w-8 h-8 p-0 hover:bg-accent"
        >
          <HelpCircle className="w-4 h-4" />
        </Button>
      </div>
    </div>
  );
}