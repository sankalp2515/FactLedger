export function AnchorText({
  text,
  anchor,
}: {
  text: string;
  anchor?: { start: number; end: number };
}) {
  const container = useRef<HTMLParagraphElement>(null);
  const valid =
    anchor &&
    Number.isInteger(anchor.start) &&
    Number.isInteger(anchor.end) &&
    anchor.start >= 0 &&
    anchor.end > anchor.start &&
    anchor.end <= text.length;
  const jump = useCallback(() => {
    const box = container.current;
    const mark = box?.querySelector("mark");
    if (box && mark)
      box.scrollTop +=
        mark.getBoundingClientRect().top - box.getBoundingClientRect().top - 24;
  }, []);
  useEffect(jump, [jump, anchor?.start, anchor?.end, text]);
  return (
    <>
      {valid && (
        <button type="button" className="text-button" onClick={jump}>
          Jump to quotation
        </button>
      )}
      <p
        className="source-text"
        ref={container}
        tabIndex={0}
        aria-label="Preserved source text"
      >
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
    </>
  );
}
import { useEffect, useRef, useCallback } from "react";
