import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { FileText, Upload } from "lucide-react";
import { motion } from "framer-motion";

type Props = { onSubmit: (file: File, title: string) => void; isSubmitting: boolean };

export function KnowledgeUploadPanel({ onSubmit, isSubmitting }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const onDrop = useCallback((accepted: File[]) => setFile(accepted[0] ?? null), []);
  const dropzone = useDropzone({
    onDrop,
    multiple: false,
    accept: { "text/markdown": [".md"], "text/plain": [".txt"], "application/pdf": [".pdf"] },
  });

  return (
    <section className="rounded-3xl border border-white/10 bg-white/[0.03] p-6 shadow-2xl shadow-black/20">
      <div
        {...dropzone.getRootProps()}
        className="cursor-pointer rounded-2xl border border-dashed border-sky-300/30 bg-sky-300/[0.03] p-10 text-center outline-none transition hover:border-sky-300/60 focus-visible:ring-2 focus-visible:ring-sky-300"
      >
        <input {...dropzone.getInputProps()} />
        <motion.div
          initial={{ scale: 0.96 }}
          animate={{ scale: 1 }}
          className="mx-auto flex w-fit rounded-2xl bg-sky-300/10 p-4 text-sky-200"
        >
          <Upload />
        </motion.div>
        <p className="mt-4 text-lg font-medium">Drop a learning resource here</p>
        <p className="mt-2 text-sm text-slate-400">or choose a file from your computer</p>
      </div>
      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <label className="text-sm text-slate-300">
          Title <span className="text-slate-500">(optional)</span>
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            className="mt-2 w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-white outline-none focus:border-sky-300"
            placeholder="A clear title"
          />
        </label>
        <div className="rounded-xl bg-black/20 p-3 text-sm text-slate-400">
          <p className="font-medium text-slate-200">Current limits</p>
          <p className="mt-1">
            Markdown, text, or digital PDF · 10 MB · 50 PDF pages · English GenAI content
          </p>
        </div>
      </div>
      {file && (
        <p className="mt-4 flex items-center gap-2 text-sm text-sky-100">
          <FileText size={16} /> {file.name}
        </p>
      )}
      <button
        disabled={!file || isSubmitting}
        onClick={() => file && onSubmit(file, title)}
        className="mt-6 w-full rounded-xl bg-sky-300 px-4 py-3 font-semibold text-slate-950 transition hover:bg-sky-200 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isSubmitting ? "Submitting resource…" : "Validate knowledge"}
      </button>
    </section>
  );
}
