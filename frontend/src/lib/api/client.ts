import createClient from "openapi-fetch";

import type { paths } from "@/lib/api/schema";

const unsafeMethods = new Set(["POST", "PUT", "PATCH", "DELETE"]);

function readCookie(name: string): string | undefined {
  if (typeof document === "undefined") {
    return undefined;
  }

  const prefix = `${encodeURIComponent(name)}=`;
  return document.cookie
    .split(";")
    .map((value) => value.trim())
    .find((value) => value.startsWith(prefix))
    ?.slice(prefix.length);
}

export const apiClient = createClient<paths>({
  credentials: "include",
});

apiClient.use({
  onRequest({ request }) {
    if (unsafeMethods.has(request.method.toUpperCase())) {
      const csrfToken = readCookie("csrftoken");
      if (csrfToken) {
        request.headers.set("X-CSRFToken", decodeURIComponent(csrfToken));
      }
    }
    return request;
  },
});
