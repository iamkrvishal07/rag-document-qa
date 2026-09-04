import {
  useEffect,
  useRef,
  useState,
} from "react";

import ReactMarkdown from "react-markdown";

import {
  askQuestion,
  exportChatHistory,
  getChatHistory,
  resetChatHistory,
} from "../api/client";

import {
  consumeSSE,
} from "../utils/sse";

import SourceBadge from "./SourceBadge";


function ChatPanel({
  documentId,
  sessionId,
  onSourceClick,
}) {
  const [question, setQuestion] =
    useState("");

  const [messages, setMessages] =
    useState([]);

  const [sending, setSending] =
    useState(false);

  const messagesEndRef =
    useRef(null);


  useEffect(() => {
    if (
      !sessionId ||
      !documentId
    ) {
      return;
    }

    let cancelled = false;

    async function loadHistory() {
      try {
        const data =
          await getChatHistory(
            sessionId,
            documentId
          );

        if (cancelled) {
          return;
        }

        const historyMessages =
          Array.isArray(data)
            ? data
            : data.messages ?? [];

        setMessages(
          historyMessages
        );
      } catch (error) {
        console.error(
          "Failed to load chat history:",
          error
        );
      }
    }

    loadHistory();

    return () => {
      cancelled = true;
    };
  }, [sessionId, documentId]);


  useEffect(() => {
    messagesEndRef.current
      ?.scrollIntoView({
        behavior: "smooth",
      });
  }, [messages]);


  const handleResetChat =
    async () => {
      if (
        !sessionId ||
        !documentId ||
        sending
      ) {
        return;
      }

      const confirmed =
        window.confirm(
          "Clear the complete chat history?"
        );

      if (!confirmed) {
        return;
      }

      try {
        await resetChatHistory(
          sessionId,
          documentId
        );

        setMessages([]);
        setQuestion("");
      } catch (error) {
        console.error(
          "Failed to reset chat:",
          error
        );
      }
    };


  const handleExportChat =
    async (format) => {
      if (
        !sessionId ||
        !documentId ||
        messages.length === 0
      ) {
        return;
      }

      try {
        await exportChatHistory(
          sessionId,
          documentId,
          format
        );
      } catch (error) {
        console.error(
          "Failed to export chat:",
          error
        );
      }
    };


  const handleSubmit =
    async (event) => {
      event.preventDefault();

      const trimmedQuestion =
        question.trim();

      if (
        !trimmedQuestion ||
        !documentId ||
        !sessionId ||
        sending
      ) {
        return;
      }

      const userMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: trimmedQuestion,
      };

      const assistantId =
        crypto.randomUUID();

      const assistantMessage = {
        id: assistantId,
        role: "assistant",
        content: "",
        sources: [],
        status: "thinking",
        notFound: false,
        error: null,
      };

      setMessages(
        (previous) => [
          ...previous,
          userMessage,
          assistantMessage,
        ]
      );

      setQuestion("");
      setSending(true);

      try {
        const response =
          await askQuestion({
            documentId,
            sessionId,
            question:
              trimmedQuestion,
          });

        await consumeSSE(
          response,
          (
            eventName,
            data
          ) => {
            if (
              eventName ===
              "start"
            ) {
              setMessages(
                (previous) =>
                  previous.map(
                    (message) =>
                      message.id ===
                      assistantId
                        ? {
                            ...message,
                            backendMessageId:
                              data.message_id,
                          }
                        : message
                  )
              );
            }

            if (
              eventName ===
              "token"
            ) {
              setMessages(
                (previous) =>
                  previous.map(
                    (message) =>
                      message.id ===
                      assistantId
                        ? {
                            ...message,
                            status:
                              "streaming",
                            content:
                              message.content +
                              (data.text ||
                                ""),
                          }
                        : message
                  )
              );
            }

            if (
              eventName ===
              "sources"
            ) {
              setMessages(
                (previous) =>
                  previous.map(
                    (message) =>
                      message.id ===
                      assistantId
                        ? {
                            ...message,
                            sources:
                              data.sources ||
                              [],
                            notFound:
                              Boolean(
                                data.not_found
                              ),
                          }
                        : message
                  )
              );
            }

            if (
              eventName ===
              "done"
            ) {
              setMessages(
                (previous) =>
                  previous.map(
                    (message) =>
                      message.id ===
                      assistantId
                        ? {
                            ...message,
                            status:
                              "complete",
                          }
                        : message
                  )
              );
            }

            if (
              eventName ===
              "error"
            ) {
              setMessages(
                (previous) =>
                  previous.map(
                    (message) =>
                      message.id ===
                      assistantId
                        ? {
                            ...message,
                            status:
                              "error",
                            error:
                              data.message ||
                              "Response interrupted.",
                          }
                        : message
                  )
              );
            }
          }
        );
      } catch (error) {
        setMessages(
          (previous) =>
            previous.map(
              (message) =>
                message.id ===
                assistantId
                  ? {
                      ...message,
                      status:
                        "error",
                      error:
                        error.message,
                    }
                  : message
            )
        );
      } finally {
        setSending(false);
      }
    };


  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="panel-header">
        <div>
          <div className="panel-label">
            AI Assistant
          </div>

          <h2 className="panel-title">
            Ask your document
          </h2>
        </div>

        <div className="chat-actions">
          <button
            type="button"
            onClick={() =>
              handleExportChat(
                "txt"
              )
            }
            disabled={
              sending ||
              messages.length === 0
            }
            className="toolbar-button"
          >
            TXT
          </button>

          <button
            type="button"
            onClick={() =>
              handleExportChat(
                "json"
              )
            }
            disabled={
              sending ||
              messages.length === 0
            }
            className="toolbar-button"
          >
            JSON
          </button>

          <button
            type="button"
            onClick={
              handleResetChat
            }
            disabled={
              sending ||
              messages.length === 0
            }
            className="toolbar-button"
          >
            Reset
          </button>
        </div>
      </div>


      <div className="chat-scroll">
        {messages.length === 0 && (
          <div className="empty-chat">
            <div className="empty-chat-icon">
              ✦
            </div>

            <h3 className="mt-5 text-lg font-semibold text-slate-900">
              Ready when you are
            </h3>

            <p className="mt-2 max-w-sm text-sm leading-6 text-slate-500">
              Ask a question and I’ll
              answer using information
              from your uploaded
              document.
            </p>

            <div className="mt-5 flex flex-wrap justify-center gap-2">
              <span className="suggestion-chip">
                Summarize this document
              </span>

              <span className="suggestion-chip">
                Explain the key ideas
              </span>

              <span className="suggestion-chip">
                What should I remember?
              </span>
            </div>
          </div>
        )}


        {messages.map(
          (message) => (
            <div
              key={message.id}
              className={
                message.role ===
                "user"
                  ? "message-row-user"
                  : "message-row-ai"
              }
            >
              {message.role ===
              "assistant" ? (
                <>
                  <div className="ai-avatar">
                    ✦
                  </div>

                  <div className="ai-message">
                    <div className="mb-2 text-xs font-semibold text-slate-500">
                      DocQuery
                    </div>

                    {message.status ===
                      "thinking" && (
                      <div className="thinking-row">
                        <span />
                        <span />
                        <span />

                        <span className="ml-2">
                          Thinking
                        </span>
                      </div>
                    )}

                    {message.content && (
                      <div className="markdown-content">
                        <ReactMarkdown>
                          {
                            message.content
                          }
                        </ReactMarkdown>
                      </div>
                    )}

                    {message.sources
                      ?.length > 0 && (
                      <div className="source-section">
                        <p className="source-label">
                          Retrieved sources
                        </p>

                        <div className="flex flex-wrap gap-2">
                          {message.sources.map(
                            (
                              source,
                              index
                            ) => (
                              <SourceBadge
                                key={`${source.type}-${source.number}-${index}`}
                                source={
                                  source
                                }
                                onClick={
                                  onSourceClick
                                }
                              />
                            )
                          )}
                        </div>
                      </div>
                    )}

                    {message.error && (
                      <div className="message-error">
                        {message.error}
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <div className="user-message">
                  {message.content}
                </div>
              )}
            </div>
          )
        )}

        <div ref={messagesEndRef} />
      </div>


      <form
        onSubmit={handleSubmit}
        className="chat-composer"
      >
        <div className="composer-inner">
          <textarea
            value={question}
            onChange={(event) =>
              setQuestion(
                event.target.value
              )
            }
            onKeyDown={(event) => {
              if (
                event.key ===
                  "Enter" &&
                !event.shiftKey
              ) {
                event.preventDefault();

                if (
                  question.trim() &&
                  !sending
                ) {
                  event.currentTarget
                    .form
                    ?.requestSubmit();
                }
              }
            }}
            rows={1}
            placeholder="Ask anything about this document..."
            disabled={sending}
            className="composer-input"
          />

          <button
            type="submit"
            disabled={
              sending ||
              !question.trim()
            }
            className="send-button"
          >
            {sending ? (
              <span className="spinner" />
            ) : (
              "↑"
            )}
          </button>
        </div>

        <p className="mt-2 text-center text-[11px] text-slate-400">
          Answers are generated only
          from the uploaded document.
        </p>
      </form>
    </div>
  );
}


export default ChatPanel;