import { type FormEvent, useState } from "react";

interface Props {
  onSubmit: (title: string, description: string) => Promise<void>;
  disabled: boolean;
}

export function RequestForm({ onSubmit, disabled }: Props) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const canSubmit =
    title.trim().length >= 3 && description.trim().length >= 1 && !disabled && !submitting;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    try {
      await onSubmit(title.trim(), description.trim());
      setTitle("");
      setDescription("");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form className="card form" onSubmit={submit}>
      <input
        className="input"
        placeholder="Feature title (min 3 characters)"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        maxLength={120}
        aria-label="Feature title"
      />
      <textarea
        className="input"
        placeholder="Describe the feature…"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        maxLength={5000}
        rows={3}
        aria-label="Feature description"
      />
      <button className="btn btn--primary" type="submit" disabled={!canSubmit}>
        {disabled ? "Identifying…" : submitting ? "Submitting…" : "Submit request"}
      </button>
    </form>
  );
}
