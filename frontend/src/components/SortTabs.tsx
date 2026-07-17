import type { SortMode } from "../types";

const MODES: { key: SortMode; label: string }[] = [
  { key: "top", label: "Top" },
  { key: "new", label: "New" },
  { key: "trending", label: "Trending" },
];

interface Props {
  sort: SortMode;
  onChange: (sort: SortMode) => void;
}

export function SortTabs({ sort, onChange }: Props) {
  return (
    <div className="tabs" role="tablist" aria-label="Sort feature requests">
      {MODES.map((mode) => (
        <button
          key={mode.key}
          role="tab"
          aria-selected={sort === mode.key}
          className={`tab ${sort === mode.key ? "tab--active" : ""}`}
          onClick={() => onChange(mode.key)}
        >
          {mode.label}
        </button>
      ))}
    </div>
  );
}
