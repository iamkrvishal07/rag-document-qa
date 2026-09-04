import {
  useEffect,
  useState,
} from "react";

import {
  createSession,
} from "../api/client";


let sessionCreationPromise = null;


export default function useSession() {
  const [sessionId, setSessionId] =
    useState(() => {
      return sessionStorage.getItem(
        "session_id"
      );
    });

  const [loading, setLoading] =
    useState(!sessionId);

  const [error, setError] = useState(null);


  useEffect(() => {
    let cancelled = false;


    async function initializeSession() {
      const existingSession =
        sessionStorage.getItem(
          "session_id"
        );

      if (existingSession) {
        if (!cancelled) {
          setSessionId(
            existingSession
          );

          setLoading(false);
        }

        return;
      }


      try {
        setLoading(true);
        setError(null);


        // React StrictMode can execute effects more than
        // once during development.
        //
        // All hook instances share one creation promise.
        if (!sessionCreationPromise) {
          sessionCreationPromise =
            createSession()
              .then((data) => {
                const id =
                  data.session_id;

                sessionStorage.setItem(
                  "session_id",
                  id
                );

                return id;
              })
              .finally(() => {
                sessionCreationPromise =
                  null;
              });
        }


        const id =
          await sessionCreationPromise;

        if (!cancelled) {
          setSessionId(id);
        }

      } catch (err) {
        console.error(
          "Session creation failed:",
          err
        );

        if (!cancelled) {
          setError(
            "Could not create session."
          );
        }

      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }


    initializeSession();


    return () => {
      cancelled = true;
    };
  }, []);


  return {
    sessionId,
    loading,
    error,
  };
}
