export const STARTERS = [
  "Find earbuds under $100",
  "Is CP-1001 in stock?",
  "Buy 2 laptops for me",
] as const;

interface Props {
  onPick: (text: string) => void;
  disabled?: boolean;
}

export function SuggestionChips({ onPick, disabled }: Props) {
  return (
    <ul className="cp-chips">
      {STARTERS.map((s, i) => (
        <li key={s}>
          <button type="button" disabled={disabled} onClick={() => onPick(s)}>
            <span>{String(i + 1).padStart(2, "0")}</span>
            {s}
          </button>
        </li>
      ))}
    </ul>
  );
}
