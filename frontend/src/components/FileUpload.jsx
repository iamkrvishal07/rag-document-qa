import {
  useRef,
  useState,
} from "react";

import {
  API_BASE_URL,
} from "../api/client";


const MAX_FILE_SIZE =
  5 * 1024 * 1024;

const ALLOWED_TYPES = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
];


function FileUpload({
  sessionId,
  onUploadSuccess,
}) {
  const inputRef = useRef(null);

  const [file, setFile] =
    useState(null);

  const [uploading, setUploading] =
    useState(false);

  const [dragging, setDragging] =
    useState(false);

  const [error, setError] =
    useState(null);


  const validateFile = (
    selectedFile
  ) => {
    if (!selectedFile) {
      return false;
    }

    if (
      !ALLOWED_TYPES.includes(
        selectedFile.type
      )
    ) {
      setError(
        "Only PDF and DOCX files are supported."
      );

      setFile(null);
      return false;
    }

    if (
      selectedFile.size >
      MAX_FILE_SIZE
    ) {
      setError(
        "File size must not exceed 5 MB."
      );

      setFile(null);
      return false;
    }

    setError(null);
    setFile(selectedFile);

    return true;
  };


  const handleFileChange = (
    event
  ) => {
    const selectedFile =
      event.target.files?.[0];

    validateFile(selectedFile);
  };


  const handleDrop = (event) => {
    event.preventDefault();

    setDragging(false);

    const droppedFile =
      event.dataTransfer.files?.[0];

    validateFile(droppedFile);
  };


  const handleUpload = async () => {
    if (!file || !sessionId) {
      return;
    }

    try {
      setUploading(true);
      setError(null);

      const formData =
        new FormData();

      formData.append(
        "file",
        file
      );

      formData.append(
        "session_id",
        sessionId
      );

      const response =
        await fetch(
          `${API_BASE_URL}/api/documents/upload`,
          {
            method: "POST",
            body: formData,
          }
        );

      const data =
        await response.json();

      if (!response.ok) {
        throw new Error(
          data.message ||
            data.error ||
            "Upload failed"
        );
      }

      onUploadSuccess(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };


  return (
    <div className="mt-10">
      <div
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() =>
          setDragging(false)
        }
        onDrop={handleDrop}
        onClick={() =>
          inputRef.current?.click()
        }
        className={`upload-zone ${
          dragging
            ? "upload-zone-active"
            : ""
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx"
          onChange={handleFileChange}
          className="hidden"
        />

        <div className="upload-icon">
          ↑
        </div>

        <h3 className="mt-5 text-lg font-semibold text-slate-900">
          Drop your document here
        </h3>

        <p className="mt-2 text-sm text-slate-500">
          or{" "}
          <span className="font-semibold text-indigo-600">
            browse files
          </span>{" "}
          from your computer
        </p>

        <div className="mt-5 flex justify-center gap-2 text-xs text-slate-400">
          <span className="file-type-pill">
            PDF
          </span>

          <span className="file-type-pill">
            DOCX
          </span>

          <span className="file-type-pill">
            Max 5 MB
          </span>
        </div>
      </div>


      {file && (
        <div className="selected-file-card">
          <div className="selected-file-icon">
            📄
          </div>

          <div className="min-w-0 flex-1 text-left">
            <p className="truncate text-sm font-semibold text-slate-800">
              {file.name}
            </p>

            <p className="text-xs text-slate-500">
              {(
                file.size /
                1024 /
                1024
              ).toFixed(2)}{" "}
              MB
            </p>
          </div>

          <span className="text-emerald-600">
            ✓
          </span>
        </div>
      )}


      {error && (
        <div className="error-message">
          {error}
        </div>
      )}


      {file && (
        <button
          type="button"
          onClick={handleUpload}
          disabled={
            !file ||
            !sessionId ||
            uploading
          }
          className="primary-button mt-5 w-full sm:w-auto"
        >
          {uploading ? (
            <>
              <span className="spinner" />
              Uploading document...
            </>
          ) : (
            <>
              Upload document
              <span>→</span>
            </>
          )}
        </button>
      )}
    </div>
  );
}


export default FileUpload;