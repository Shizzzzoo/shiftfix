import { useId, useState } from "react";
import { ImagePlus } from "lucide-react";
import { validateImages } from "../uploads";
export function PhotoInput({
  files,
  onChange,
  label = "Add photo evidence",
}: {
  files: File[];
  onChange: (files: File[]) => void;
  label?: string;
}) {
  const id = useId();
  const [error, setError] = useState("");
  return (
    <div className="photo-field">
      <label className="upload" htmlFor={id}>
        <ImagePlus aria-hidden="true" />
        <strong>{label}</strong>
        <span id={id + "-help"}>
          Up to 5 images · JPEG, PNG, WebP · 5 MB each
        </span>
        <input
          id={id}
          type="file"
          multiple
          accept="image/jpeg,image/png,image/webp"
          aria-describedby={id + "-help " + id + "-error"}
          aria-invalid={!!error}
          onChange={(e) => {
            try {
              const chosen = Array.from(e.target.files || []);
              validateImages(chosen);
              onChange(chosen);
              setError("");
              e.target.setCustomValidity("");
            } catch (err) {
              setError((err as Error).message);
              onChange([]);
              e.target.value = "";
              e.target.setCustomValidity((err as Error).message);
            }
          }}
        />
      </label>
      <p className="file-list" aria-live="polite">
        {files
          .map((f) => `${f.name} (${(f.size / 1024).toFixed(0)} KB)`)
          .join(", ")}
      </p>
      <div
        id={id + "-error"}
        role="alert"
        className={error ? "notice error" : ""}
      >
        {error}
      </div>
      {error && (
        <button
          type="button"
          onClick={() => {
            setError("");
            const input = document.getElementById(id) as HTMLInputElement;
            if (input) {
              input.value = "";
              input.setCustomValidity("");
            }
          }}
        >
          Continue without this image
        </button>
      )}
      {files.length > 0 && (
        <button
          type="button"
          onClick={() => {
            onChange([]);
            setError("");
            const input = document.getElementById(id) as HTMLInputElement;
            if (input) {
              input.value = "";
              input.setCustomValidity("");
            }
          }}
        >
          Remove selected images
        </button>
      )}
    </div>
  );
}
