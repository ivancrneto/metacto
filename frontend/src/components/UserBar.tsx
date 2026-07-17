import { type ChangeEvent } from "react";

interface Props {
  user: string;
  onChange: (user: string) => void;
}

export function UserBar({ user, onChange }: Props) {
  const handle = (e: ChangeEvent<HTMLInputElement>) => {
    onChange(e.target.value.trim().toLowerCase());
  };

  return (
    <label className="userbar">
      <span className="muted">You are</span>
      <input
        className="input input--user"
        placeholder="username"
        value={user}
        onChange={handle}
        maxLength={50}
        aria-label="Your username"
      />
    </label>
  );
}
