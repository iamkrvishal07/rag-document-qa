import {
  useEffect,
  useState,
} from "react";

import {
  getDocumentPreview,
} from "../api/client";


function DocumentViewer({
  documentId,
}) {
  const [preview, setPreview] =
    useState(null);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState(null);


  useEffect(() => {
    if (!documentId) {
      return;
    }

    const loadPreview =
      async () => {
        try {
          setLoading(true);
          setError(null);

          const data =
            await getDocumentPreview(
              documentId
            );

          setPreview(data);
        } catch (err) {
          setError(err.message);
        } finally {
          setLoading(false);
        }
      };

    loadPreview();
  }, [documentId]);


  if (loading) {
    return (
      <div className="panel-loading">
        <span className="spinner-dark" />
        Loading document preview...
      </div>
    );
  }


  if (error) {
    return (
      <div className="status-error m-5">
        Preview error: {error}
      </div>
    );
  }


  if (!preview) {
    return null;
  }


  return (
    <div className="flex h-full flex-col">
      <div className="panel-header">
        <div>
          <div className="panel-label">
            Document
          </div>

          <h2 className="panel-title">
            Document Preview
          </h2>
        </div>

        <div className="unit-count">
          {preview.total_units}{" "}
          {preview.file_type ===
          "pdf"
            ? "pages"
            : "sections"}
        </div>
      </div>


      <div className="document-scroll">
        {preview.units.map(
          (unit) => (
            <article
              key={unit.number}
              id={`${preview.unit}-${unit.number}`}
              className="document-unit"
            >
              <div className="mb-4 flex items-center justify-between gap-3">
                <span className="page-badge">
                  {preview.unit ===
                  "page"
                    ? `Page ${unit.number}`
                    : `Section ${unit.number}`}
                </span>

                <span className="text-xs text-slate-400">
                  #
                  {String(
                    unit.number
                  ).padStart(2, "0")}
                </span>
              </div>

              {unit.heading && (
                <h3 className="mb-3 font-semibold text-slate-900">
                  {unit.heading}
                </h3>
              )}

              <p className="whitespace-pre-wrap text-sm leading-7 text-slate-600">
                {unit.text_preview}
              </p>
            </article>
          )
        )}
      </div>
    </div>
  );
}


export default DocumentViewer;