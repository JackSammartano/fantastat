interface StatePanelProps {
  title: string;
  message: string;
  tone?: "neutral" | "error";
}

export function StatePanel({
  title,
  message,
  tone = "neutral"
}: StatePanelProps) {
  return (
    <div className={`state-panel state-panel--${tone}`} role="status">
      <strong>{title}</strong>
      <span>{message}</span>
    </div>
  );
}

