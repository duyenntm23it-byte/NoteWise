import { ImageResponse } from "next/og";

export const alt = "NoteWise learning workspace";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpenGraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          display: "flex",
          height: "100%",
          width: "100%",
          alignItems: "center",
          justifyContent: "center",
          background: "#f8fafc",
          color: "#1e1b4b",
          fontSize: 88,
          fontWeight: 700,
        }}
      >
        <span
          style={{
            display: "flex",
            width: 120,
            height: 120,
            alignItems: "center",
            justifyContent: "center",
            marginRight: 28,
            borderRadius: 28,
            background: "#4f46e5",
            color: "#ffffff",
          }}
        >
          N
        </span>
        NoteWise
      </div>
    ),
    size,
  );
}
