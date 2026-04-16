import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  createApplication,
  getApplication,
  getPresignedUrl,
  getUploadContentType,
  toApiErrorMessage,
  type ApplicationResponse,
} from "@/services/api";

type UploadState = "idle" | "uploading" | "processing" | "completed" | "failed";

const POLL_INTERVAL_MS = 2500;
const POLL_TIMEOUT_MS = 5 * 60 * 1000;

function isTerminalStatus(status: string): boolean {
  return status === "completed" || status === "failed";
}

function statusFromApplication(application: ApplicationResponse): UploadState {
  if (application.status === "completed") {
    return "completed";
  }

  if (application.status === "failed") {
    return "failed";
  }

  return "processing";
}

export default function UploadPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadState, setUploadState] = useState<UploadState>("idle");
  const [statusMessage, setStatusMessage] = useState("Choose a resume file to begin.");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [application, setApplication] = useState<ApplicationResponse | null>(null);
  const [applicationId, setApplicationId] = useState<string | null>(null);
  const [idempotencyKey, setIdempotencyKey] = useState<string | null>(null);

  useEffect(() => {
    if (uploadState !== "processing" || !applicationId) {
      return undefined;
    }

    let cancelled = false;
    let timeoutHandle: number | null = null;
    const startedAt = Date.now();

    const pollApplication = async () => {
      if (cancelled) {
        return;
      }

      if (Date.now() - startedAt >= POLL_TIMEOUT_MS) {
        setUploadState("failed");
        setErrorMessage("Processing timed out before the application finished.");
        setStatusMessage("Processing timed out.");
        return;
      }

      try {
        const nextApplication = await getApplication(applicationId);
        if (cancelled) {
          return;
        }

        setApplication(nextApplication);

        if (nextApplication.status === "completed") {
          setUploadState("completed");
          setErrorMessage(null);
          setStatusMessage("Application processing completed.");
          return;
        }

        if (nextApplication.status === "failed") {
          setUploadState("failed");
          setErrorMessage("Application processing failed.");
          setStatusMessage("Application processing failed.");
          return;
        }

        timeoutHandle = window.setTimeout(pollApplication, POLL_INTERVAL_MS);
      } catch (error) {
        if (cancelled) {
          return;
        }

        setUploadState("failed");
        setErrorMessage(
          toApiErrorMessage(error, "Failed to fetch the latest application status."),
        );
        setStatusMessage("Application polling failed.");
      }
    };

    timeoutHandle = window.setTimeout(pollApplication, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      if (timeoutHandle !== null) {
        window.clearTimeout(timeoutHandle);
      }
    };
  }, [applicationId, uploadState]);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    event.target.value = "";

    setSelectedFile(file);
    setApplication(null);
    setApplicationId(null);
    setIdempotencyKey(file ? crypto.randomUUID() : null);
    setErrorMessage(null);
    setUploadState("idle");
    setStatusMessage(file ? `Ready to upload ${file.name}.` : "Choose a resume file to begin.");
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setErrorMessage("Select a PDF or DOCX file first.");
      return;
    }

    const currentIdempotencyKey = idempotencyKey ?? crypto.randomUUID();
    setIdempotencyKey(currentIdempotencyKey);
    setUploadState("uploading");
    setApplication(null);
    setApplicationId(null);
    setErrorMessage(null);
    setStatusMessage("Requesting a presigned upload URL.");

    try {
      getUploadContentType(selectedFile);
      const presignedUpload = await getPresignedUrl(selectedFile);

      setStatusMessage("Uploading the file to storage.");
      const uploadResponse = await fetch(presignedUpload.upload_url, {
        method: "PUT",
        headers: presignedUpload.upload_headers,
        body: selectedFile,
      });

      if (!uploadResponse.ok) {
        throw new Error(`File upload failed with status ${uploadResponse.status}.`);
      }

      setStatusMessage("Creating the application.");
      const createdApplication = await createApplication(
        presignedUpload.file_url,
        currentIdempotencyKey,
      );

      setApplication(createdApplication);
      setApplicationId(createdApplication.application_id);
      setUploadState(statusFromApplication(createdApplication));

      if (createdApplication.status === "completed") {
        setStatusMessage("Application processing completed.");
        return;
      }

      if (createdApplication.status === "failed") {
        setErrorMessage("Application processing failed.");
        setStatusMessage("Application processing failed.");
        return;
      }

      setStatusMessage("Application created. Waiting for background processing.");
    } catch (error) {
      setUploadState("failed");
      setErrorMessage(
        toApiErrorMessage(error, "Upload flow failed before processing could start."),
      );
      setStatusMessage("Upload flow failed.");
    }
  };

  const canUpload = selectedFile !== null && uploadState !== "uploading" && uploadState !== "processing";
  const scoreBreakdown = application?.score_breakdown
    ? JSON.stringify(application.score_breakdown, null, 2)
    : null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Upload Resume</h1>
        <p className="text-muted-foreground">
          Upload a resume, create an application, and track worker progress.
        </p>
      </div>

      <div className="space-y-4 rounded-lg border bg-card p-6">
        <div className="space-y-2">
          <label htmlFor="resume-upload" className="text-sm font-medium">
            Resume file
          </label>
          <Input
            id="resume-upload"
            type="file"
            accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            onChange={handleFileChange}
          />
        </div>

        <Button onClick={handleUpload} disabled={!canUpload}>
          {uploadState === "uploading"
            ? "Uploading..."
            : uploadState === "processing"
              ? "Processing..."
              : "Upload Resume"}
        </Button>

        <div className="space-y-2 text-sm">
          <p>
            <span className="font-medium">State:</span> {uploadState}
          </p>
          <p>
            <span className="font-medium">Status:</span> {statusMessage}
          </p>
          {selectedFile ? (
            <p>
              <span className="font-medium">Selected file:</span> {selectedFile.name}
            </p>
          ) : null}
          {applicationId ? (
            <p>
              <span className="font-medium">Application ID:</span> {applicationId}
            </p>
          ) : null}
          {application?.status ? (
            <p>
              <span className="font-medium">Application status:</span> {application.status}
            </p>
          ) : null}
          {errorMessage ? (
            <p className="text-destructive">
              <span className="font-medium">Error:</span> {errorMessage}
            </p>
          ) : null}
        </div>
      </div>

      {(application !== null || uploadState === "completed") && (
        <div className="space-y-4 rounded-lg border bg-card p-6">
          <h2 className="text-xl font-semibold">Result</h2>
          <p className="text-sm text-muted-foreground">
            Completed applications show score details when the API returns them.
          </p>

          {typeof application?.score === "number" ? (
            <p>
              <span className="font-medium">Score:</span> {application.score}
            </p>
          ) : (
            <p className="text-sm text-muted-foreground">Score is not available yet.</p>
          )}

          {scoreBreakdown ? (
            <pre className="overflow-x-auto rounded-md bg-muted p-4 text-sm">
              {scoreBreakdown}
            </pre>
          ) : (
            <p className="text-sm text-muted-foreground">
              Score breakdown is not available yet.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
