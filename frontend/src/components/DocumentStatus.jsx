import {
  useEffect,
  useState,
} from "react";

import {
  API_BASE_URL,
} from "../api/client";


const LABELS = {
  extracting_text:
    "Extracting document text",
  splitting_document:
    "Preparing document chunks",
  creating_embeddings:
    "Creating semantic embeddings",
  indexing_document:
    "Building searchable index",
  ready:
    "Document ready",
};


function DocumentStatus({
  documentId,
  onReady,
}) {
  const [status, setStatus] =
    useState("processing");

  const [detail, setDetail] =
    useState("extracting_text");

  const [progress, setProgress] =
    useState(0);

  const [error, setError] =
    useState(null);


  useEffect(() => {
    if (!documentId) {
      return;
    }

    let intervalId;

    const checkStatus =
      async () => {
        try {
          const response =
            await fetch(
              `${API_BASE_URL}/api/documents/${documentId}/status`
            );

          const data =
            await response.json();

          if (!response.ok) {
            throw new Error(
              data.message ||
                data.error ||
                "Failed to check status"
            );
          }

          setStatus(data.status);

          setDetail(
            data.status_detail || ""
          );

          setProgress(
            data.progress_percent ||
              (data.status === "ready"
                ? 100
                : 0)
          );

          if (
            data.status === "ready"
          ) {
            clearInterval(
              intervalId
            );

            onReady?.(data);
          }

          if (
            data.status === "failed"
          ) {
            clearInterval(
              intervalId
            );

            setError(
              data.message ||
                data.error ||
                "Document processing failed"
            );
          }
        } catch (err) {
          clearInterval(intervalId);

          setError(err.message);
        }
      };


    checkStatus();

    intervalId = setInterval(
      checkStatus,
      1500
    );

    return () => {
      clearInterval(intervalId);
    };
  }, [documentId, onReady]);


  if (error) {
    return (
      <div className="status-error">
        <span>!</span>

        <div>
          <p className="font-semibold">
            Processing failed
          </p>

          <p className="text-sm">
            {error}
          </p>
        </div>
      </div>
    );
  }


  if (status === "ready") {
    return (
      <div className="ready-banner">
        <div className="ready-check">
          ✓
        </div>

        <div>
          <p className="font-semibold text-slate-800">
            Document ready
          </p>

          <p className="text-sm text-slate-500">
            You can now explore and
            ask questions.
          </p>
        </div>
      </div>
    );
  }


  return (
    <div className="processing-card">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="font-semibold text-slate-800">
            Preparing your document
          </p>

          <p className="mt-1 text-sm text-slate-500">
            {LABELS[detail] ||
              "Processing document"}
          </p>
        </div>

        <span className="text-sm font-semibold text-indigo-600">
          {progress}%
        </span>
      </div>

      <div className="progress-track">
        <div
          className="progress-value"
          style={{
            width: `${progress}%`,
          }}
        />
      </div>
    </div>
  );
}


export default DocumentStatus;