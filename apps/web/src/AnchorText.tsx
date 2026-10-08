export function AnchorText({
  text,
  anchor,
}: {
  text: string;
  anchor?: { start: number; end: number };
}) {
  const valid =
    anchor &&
    Number.isInteger(anchor.start) &&
    Number.isInteger(anchor.end) &&
    anchor.start >= 0 &&
    anchor.end > anchor.start &&
    anchor.end <= text.length;
  return (
    <p className="source-text">
      {valid ? (
        <>
          {text.slice(0, anchor.start)}
          <mark tabIndex={0}>{text.slice(anchor.start, anchor.end)}</mark>
          {text.slice(anchor.end)}
        </>
      ) : (
        text
      )}
    </p>
  );
}
