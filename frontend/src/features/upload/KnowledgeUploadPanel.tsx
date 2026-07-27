import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { FileText, Upload, X } from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";

type Props = { onSubmit: (file: File, title: string) => void; isSubmitting: boolean };

function formatFileSize(size: number) {
  if (size < 1024 * 1024) return `${Math.max(1, Math.round(size / 1024))} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

export function KnowledgeUploadPanel({ onSubmit, isSubmitting }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const reducedMotion = useReducedMotion();
  const onDrop = useCallback((accepted: File[]) => setFile(accepted[0] ?? null), []);
  const dropzone = useDropzone({
    onDrop,
    multiple: false,
    disabled: isSubmitting,
    noClick: Boolean(file),
    noKeyboard: Boolean(file),
    accept: { "text/markdown": [".md"], "text/plain": [".txt"], "application/pdf": [".pdf"] },
  });

  return (
    <div className="upload-workspace">
      <div
        {...dropzone.getRootProps({
          "aria-label": "Choose a Generative AI learning resource to review",
          role: file ? undefined : "button",
          className: `document-dropzone${dropzone.isDragActive ? " is-active" : ""}${
            file ? " has-file" : ""
          }`,
        })}
      >
        <input {...dropzone.getInputProps()} />
        {!file ? (
          <>
            <motion.div
              className="dropzone-icon"
              initial={{ opacity: 0, scale: reducedMotion ? 1 : 0.88 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: reducedMotion ? 0 : 0.32 }}
              aria-hidden="true"
            >
              <Upload size={22} />
            </motion.div>
            <p className="dropzone-title">Drop a GenAI learning resource here</p>
            <p className="dropzone-copy">
              Drag and drop, or <span>choose a file</span> from your computer.
            </p>
          </>
        ) : (
          <div className="selected-file" onClick={(event) => event.stopPropagation()}>
            <span className="selected-file-icon" aria-hidden="true">
              <FileText size={19} />
            </span>
            <span className="selected-file-meta">
              <strong>{file.name}</strong>
              <small>
                {file.type === "application/pdf"
                  ? "PDF"
                  : file.name.split(".").pop()?.toUpperCase()}{" "}
                · {formatFileSize(file.size)}
              </small>
            </span>
            <button
              className="replace-file"
              type="button"
              onClick={() => dropzone.open()}
              disabled={isSubmitting}
            >
              Replace
            </button>
            <button
              className="icon-button"
              type="button"
              onClick={() => setFile(null)}
              aria-label="Remove selected file"
              disabled={isSubmitting}
            >
              <X size={17} />
            </button>
          </div>
        )}
      </div>
      <div className="upload-details">
        <label className="quiet-field">
          <span>
            Title <small>Optional</small>
          </span>
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Give this resource a clear title"
            disabled={isSubmitting}
          />
        </label>
        <p className="upload-guidance">
          <strong>PDF, Markdown, or text</strong>
          <span>Up to 10 MB · Up to 50 PDF pages · English GenAI learning material</span>
        </p>
      </div>
      <button
        disabled={!file || isSubmitting}
        onClick={() => file && onSubmit(file, title)}
        className="button button-primary review-resource-action"
      >
        {isSubmitting ? "Adding your resource…" : "Review this resource"}
      </button>
    </div>
  );
}
