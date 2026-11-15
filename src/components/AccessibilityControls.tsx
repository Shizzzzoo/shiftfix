export type AccessibilityProps = {
  contrast: boolean;
  largeText: boolean;
  onContrast: () => void;
  onLargeText: () => void;
};
export function AccessibilityControls({
  contrast,
  largeText,
  onContrast,
  onLargeText,
}: AccessibilityProps) {
  return (
    <div className="accessibility-controls">
      <div className="preference">
        <div>
          <h3>High contrast</h3>
          <p>
            Stronger text and borders. Every status also has a written label.
          </p>
        </div>
        <button type="button" aria-pressed={contrast} onClick={onContrast}>
          {contrast ? "High contrast on" : "Turn on high contrast"}
        </button>
      </div>
      <div className="preference">
        <div>
          <h3>Larger interface text</h3>
          <p>
            Make tables, forms and repair details easier to read. Browser zoom
            works too.
          </p>
        </div>
        <button type="button" aria-pressed={largeText} onClick={onLargeText}>
          {largeText ? "Larger text on" : "Use larger text"}
        </button>
      </div>
    </div>
  );
}
