import { GitBranch, Plus, Users } from "lucide-react";
import type { AppView } from "@/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface QuickActionsCardProps {
  onNavigate: (view: AppView) => void;
  onNewPath: () => void;
  onNewAccount: () => void;
}

export function QuickActionsCard({ onNavigate, onNewPath, onNewAccount }: QuickActionsCardProps) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Quick actions</CardTitle>
        <CardDescription>Start from here.</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        <Button type="button" variant="secondary" className="justify-start" onClick={onNewPath}>
          <Plus className="size-4" />
          New Path
        </Button>
        <Button type="button" variant="secondary" className="justify-start" onClick={onNewAccount}>
          <Users className="size-4" />
          New Account
        </Button>
        <Button
          type="button"
          variant="outline"
          className="justify-start"
          onClick={() => onNavigate({ category: "paths" })}
        >
          <GitBranch className="size-4" />
          Path Library
        </Button>
        <Button
          type="button"
          variant="outline"
          className="justify-start"
          onClick={() => onNavigate({ category: "accounts" })}
        >
          <Users className="size-4" />
          Accounts
        </Button>
      </CardContent>
    </Card>
  );
}
