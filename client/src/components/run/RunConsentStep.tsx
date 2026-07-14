import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";

interface RunConsentStepProps {
  consentChecked: boolean;
  onConsentChange: (checked: boolean) => void;
  loading: boolean;
  error: string | null;
  onDecline: () => void;
  onAccept: () => void;
}

export function RunConsentStep({
  consentChecked,
  onConsentChange,
  loading,
  error,
  onDecline,
  onAccept,
}: RunConsentStepProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Consent & Authorization</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Pathline is client-mediated. Your device places the call, holds your Inputs and Secrets,
          and processes audio locally. The server only receives encrypted Status blobs.
        </p>

        <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
          <li>Your Secrets and target number stay on this device — never sent to our servers</li>
          <li>Speech recognition runs locally when available</li>
          <li>Only encrypted Status is reported to Pathline</li>
          <li>Run data is auto-purged; you can revoke and delete anytime</li>
          <li>Carriers still see calling/called numbers, times, and duration</li>
          <li>You confirm lawful usage and authorization for third-party IVR interactions</li>
        </ul>

        <label className="flex cursor-pointer items-start gap-3 text-sm">
          <Checkbox
            checked={consentChecked}
            onCheckedChange={(checked) => onConsentChange(checked === true)}
          />
          <span>I have read and accept these terms (v1.0)</span>
        </label>

        {error && (
          <Alert variant="destructive">
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
      </CardContent>
      <CardFooter className="flex justify-end gap-2 border-t">
        <Button type="button" variant="outline" onClick={onDecline}>
          Decline
        </Button>
        <Button type="button" disabled={!consentChecked || loading} onClick={onAccept}>
          Accept & Continue
        </Button>
      </CardFooter>
    </Card>
  );
}
