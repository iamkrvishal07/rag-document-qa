import {
  useEffect,
  useState,
} from "react";

import {
  deleteDocument,
} from "./api/client";

import ChatPanel from "./components/ChatPanel";
import DocumentStatus from "./components/DocumentStatus";
import DocumentViewer from "./components/DocumentViewer";
import FileUpload from "./components/FileUpload";
import Header from "./components/Header";

import useSession from "./hooks/useSession";


function App() {
  const {
    sessionId,
    loading,
    error,
  } = useSession();

  const [document, setDocument] =
    useState(() => {
      const saved =
        sessionStorage.getItem(
          "current_document"
        );

      return saved
        ? JSON.parse(saved)
        : null;
    });

  const [
    documentReady,
    setDocumentReady,
  ] = useState(false);

  const [
    deleting,
    setDeleting,
  ] = useState(false);


  useEffect(() => {
    if (document) {
      sessionStorage.setItem(
        "current_document",
        JSON.stringify(document)
      );
    } else {
      sessionStorage.removeItem(
        "current_document"
      );
    }
  }, [document]);


  const handleDeleteDocument =
    async () => {
      if (!document || deleting) {
        return;
      }

      const confirmed =
        window.confirm(
          "Delete this document and its chat history?"
        );

      if (!confirmed) {
        return;
      }

      try {
        setDeleting(true);

        await deleteDocument(
          document.document_id
        );

        setDocument(null);
        setDocumentReady(false);

        sessionStorage.removeItem(
          "current_document"
        );
      } catch (error) {
        console.error(
          "Failed to delete document:",
          error
        );
      } finally {
        setDeleting(false);
      }
    };


  const handleSourceClick = (
    source
  ) => {
    const targetId =
      `${source.type}-${source.number}`;

    const element =
      window.document.getElementById(
        targetId
      );

    if (element) {
      element.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });

      element.classList.add(
        "source-highlight"
      );

      window.setTimeout(() => {
        element.classList.remove(
          "source-highlight"
        );
      }, 1800);
    }
  };


  if (loading) {
    return (
      <div className="app-loading">
        <div className="loading-logo">
          ✦
        </div>

        <p>Preparing your workspace...</p>
      </div>
    );
  }


  if (error) {
    return (
      <div className="app-loading">
        <div className="error-card">
          <h2>
            Unable to start session
          </h2>

          <p>{error}</p>
        </div>
      </div>
    );
  }


  return (
    <div className="min-h-screen bg-slate-50">
      <Header />

      <main className="mx-auto max-w-[1500px] px-4 py-6 sm:px-6 lg:px-8">
        {!document && (
          <section className="upload-hero">
            <div className="mx-auto max-w-3xl text-center">
              <div className="hero-badge">
                ✦ AI Document Assistant
              </div>

              <h1 className="hero-title">
                Turn your documents into
                conversations.
              </h1>

              <p className="hero-description">
                Upload a PDF or DOCX and ask
                questions using information
                grounded in your document.
              </p>

              <FileUpload
                sessionId={sessionId}
                onUploadSuccess={(data) => {
                  setDocument(data);
                  setDocumentReady(false);
                }}
              />
            </div>
          </section>
        )}


        {document && (
          <>
            <section className="document-toolbar">
              <div className="min-w-0">
                <div className="flex items-center gap-3">
                  <div className="document-icon">
                    {document.file_type ===
                    "pdf"
                      ? "PDF"
                      : "DOC"}
                  </div>

                  <div className="min-w-0">
                    <h2 className="truncate text-base font-semibold text-slate-900">
                      {document.filename}
                    </h2>

                    <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                      <span className="rounded-full bg-slate-100 px-2 py-1 uppercase">
                        {document.file_type}
                      </span>

                      {document.file_size_bytes && (
                        <span>
                          {(
                            document.file_size_bytes /
                            1024 /
                            1024
                          ).toFixed(2)}{" "}
                          MB
                        </span>
                      )}

                      <span className="hidden sm:inline">
                        •
                      </span>

                      <span className="hidden max-w-[320px] truncate sm:inline">
                        {
                          document.document_id
                        }
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <button
                type="button"
                onClick={
                  handleDeleteDocument
                }
                disabled={deleting}
                className="danger-button"
              >
                <span>⌫</span>

                {deleting
                  ? "Deleting..."
                  : "Delete"}
              </button>
            </section>


            <DocumentStatus
              documentId={
                document.document_id
              }
              onReady={() => {
                setDocumentReady(true);
              }}
            />


            {documentReady && (
              <section className="workspace-grid">
                <div className="workspace-card">
                  <DocumentViewer
                    documentId={
                      document.document_id
                    }
                  />
                </div>

                <div className="workspace-card">
                  <ChatPanel
                    documentId={
                      document.document_id
                    }
                    sessionId={sessionId}
                    onSourceClick={
                      handleSourceClick
                    }
                  />
                </div>
              </section>
            )}
          </>
        )}
      </main>
    </div>
  );
}


export default App;
