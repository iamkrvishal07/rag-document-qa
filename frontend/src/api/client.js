const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000";

export async function createSession() {
  const response = await fetch(
    `${API_BASE_URL}/session`,
    {
      method: "POST",
    }
  );

  if (!response.ok) {
    throw new Error(
      "Failed to create session"
    );
  }

  return response.json();
}

export async function askQuestion({
  documentId,
  sessionId,
  question,
}) {
  const response = await fetch(
    `${API_BASE_URL}/api/chat/${documentId}/ask`,
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        session_id: sessionId,
        question,
      }),
    }
  );

  if (!response.ok) {
    let message =
      "Failed to send question.";

    try {
      const data =
        await response.json();

      message =
        data.message ||
        data.error ||
        message;
    } catch {
      // Keep default message.
    }

    throw new Error(message);
  }

  return response;
}

export async function getDocumentPreview(
  documentId
) {
  const response = await fetch(
    `${API_BASE_URL}/api/documents/${documentId}/preview`
  );

  if (!response.ok) {
    let message =
      "Failed to load document preview.";

    try {
      const data =
        await response.json();

      message =
        data.message ||
        data.error ||
        message;
    } catch {
      // Keep default message.
    }

    throw new Error(message);
  }

  return response.json();
}

export async function getChatHistory(
  sessionId,
  documentId
) {
  const response = await fetch(
    `${API_BASE_URL}/api/chat/${sessionId}/${documentId}/history`
  );

  if (!response.ok) {
    throw new Error("Failed to load chat history");
  }

  return response.json();
}

export async function resetChatHistory(
  sessionId,
  documentId
) {
  const response = await fetch(
    `${API_BASE_URL}/api/chat/${sessionId}/${documentId}/reset`,
    {
      method: "POST",
    }
  );

  if (!response.ok) {
    throw new Error(
      "Failed to reset chat history"
    );
  }
}

export async function exportChatHistory(
  sessionId,
  documentId,
  format = "txt"
) {
  const response = await fetch(
    `${API_BASE_URL}/api/chat/${sessionId}/${documentId}/export?format=${format}`
  );

  if (!response.ok) {
    throw new Error(
      "Failed to export chat history"
    );
  }

  const blob = await response.blob();

  const url =
    window.URL.createObjectURL(blob);

  const link =
    window.document.createElement("a");

  link.href = url;

  link.download =
    format === "json"
      ? "conversation.json"
      : "conversation.txt";

  window.document.body.appendChild(
    link
  );

  link.click();

  link.remove();

  window.URL.revokeObjectURL(url);
}

export async function deleteDocument(
  documentId
) {
  const response = await fetch(
    `${API_BASE_URL}/api/documents/${documentId}`,
    {
      method: "DELETE",
    }
  );

  if (!response.ok) {
    throw new Error(
      "Failed to delete document"
    );
  }
}

export { API_BASE_URL };
