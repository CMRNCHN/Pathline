import { KeyRound, Shield } from "lucide-react";
import { clearLocalKeys } from "@/crypto";
import { isLocalWhisperAvailable } from "@/stt/whisperEngine";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function CryptoSection() {
  const whisperReady = isLocalWhisperAvailable();

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center gap-3">
          <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Shield className="size-4" />
          </div>
          <CardTitle>Privacy & crypto</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <div className="flex items-center justify-between gap-2">
          <span className="text-muted-foreground">Local STT (Whisper)</span>
          <Badge variant={whisperReady ? "default" : "secondary"}>
            {whisperReady ? "Ready" : "Unavailable"}
          </Badge>
        </div>
        <p className="text-muted-foreground">
          Secrets, targets, and audio stay on this device. Input Vault seals values with a
          device key.
        </p>
        <Button
          type="button"
          variant="outline"
          onClick={() => {
            if (!confirm("Clear local encryption keys on this device?")) return;
            clearLocalKeys();
            alert("Session and vault device keys cleared.");
          }}
        >
          <KeyRound className="size-4" />
          Clear encryption keys
        </Button>
      </CardContent>
    </Card>
  );
}
