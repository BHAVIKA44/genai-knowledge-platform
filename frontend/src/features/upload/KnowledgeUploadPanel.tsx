import { useCallback, useEffect, useState } from "react";
import { useDropzone } from "react-dropzone";
import { ChevronDown, FileText, Upload, X } from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";

type Props = {
  onSubmit: (file: File, title: string) => void;
  isSubmitting: boolean;
  error?: string | null;
  resetKey?: number;
};

function formatFileSize(size: number) {
  if (size < 1024 * 1024) return `${Math.max(1, Math.round(size / 1024))} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

export function KnowledgeUploadPanel({ onSubmit, isSubmitting, error, resetKey = 0 }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const reducedMotion = useReducedMotion();
  useEffect(() => {
    setFile(null);
    setTitle("");
  }, [resetKey]);
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
          }${isSubmitting ? " is-disabled" : ""}`,
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
            <div className="accepted-format-badges" aria-hidden="true">
              <span>PDF</span>
              <span>.MD</span>
              <span>.TXT</span>
            </div>
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
      </div>
      <details className="upload-requirements">
        <summary>
          <span>SYSTEM REQUIREMENTS &amp; CONSTRAINTS</span>
          <ChevronDown size={15} aria-hidden="true" />
        </summary>
        <div>
          <section>
            <p>Upload limits</p>
            <ul>
              <li>Up to 10 MB</li>
              <li>PDFs up to 50 pages</li>
              <li>Digital PDFs only</li>
            </ul>
          </section>
          <section>
            <p>Content requirements</p>
            <ul>
              <li>English GenAI learning material</li>
              <li>Content needs at least 150 meaningful characters</li>
              <li>Digital PDFs need selectable text</li>
            </ul>
          </section>
          <section>
            <p>Review and availability</p>
            <ul>
              <li>Title is optional</li>
              <li>Exact duplicate files are rejected</li>
              <li>Resources may require review before becoming searchable</li>
              <li>Only accepted resources become searchable</li>
            </ul>
          </section>
          <section>
            <p>Not supported</p>
            <ul>
              <li>images, DOCX, HTML, or scanned PDFs</li>
            </ul>
          </section>
        </div>
      </details>
      <button
        disabled={!file || isSubmitting}
        onClick={() => file && onSubmit(file, title)}
        className="button button-primary review-resource-action"
      >
        {isSubmitting ? "Adding your resource…" : "Review this resource"}
      </button>
      {error && (
        <p className="safe-error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
