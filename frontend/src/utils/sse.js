export async function consumeSSE(
  response,
  onEvent
) {
  if (!response.body) {
    throw new Error(
      "Streaming response is not available."
    );
  }

  const reader =
    response.body.getReader();

  const decoder =
    new TextDecoder("utf-8");

  let buffer = "";

  try {
    while (true) {
      const {
        value,
        done,
      } = await reader.read();

      if (done) {
        break;
      }

      buffer += decoder.decode(
        value,
        {
          stream: true,
        }
      );

      const events =
        buffer.split("\n\n");

      buffer =
        events.pop() || "";

      for (const rawEvent of events) {
        if (!rawEvent.trim()) {
          continue;
        }

        let eventName = null;
        let data = null;

        const lines =
          rawEvent.split("\n");

        for (const line of lines) {
          if (
            line.startsWith("event:")
          ) {
            eventName = line
              .slice(6)
              .trim();
          }

          if (
            line.startsWith("data:")
          ) {
            const rawData = line
              .slice(5)
              .trim();

            try {
              data =
                JSON.parse(rawData);
            } catch {
              data = {
                text: rawData,
              };
            }
          }
        }

        if (
          eventName &&
          data !== null
        ) {
          onEvent(
            eventName,
            data
          );
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
