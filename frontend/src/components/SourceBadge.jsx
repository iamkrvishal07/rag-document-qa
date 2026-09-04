function SourceBadge({
  source,
  onClick,
}) {
  if (!source) {
    return null;
  }

  const label =
    source.type === "page"
      ? `Page ${source.number}`
      : `Section ${source.number}`;

  return (
    <button
      type="button"
      onClick={() =>
        onClick?.(source)
      }
      className="source-badge"
      title={
        source.heading || label
      }
    >
      <span>⌖</span>
      {label}
      <span className="source-arrow">
        →
      </span>
    </button>
  );
}


export default SourceBadge;