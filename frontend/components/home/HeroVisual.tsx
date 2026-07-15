/** An original, abstract stand-in for the Lead Finder pipeline — four
 * sharp-edged nodes (Suche → Analyse → Draft → Review) joined by thin
 * lines over a faint hairline grid. Pure SVG, no photography, no
 * gradients, no rounded/pill shapes — matches the app's existing kantig
 * design language rather than the reference site's blurred-portrait hero.
 * Purely decorative (the same information is already stated in real text
 * around it), so it is `aria-hidden`. */
export function HeroVisual({ className }: { className?: string }) {
  const nodes = [
    { x: 40, y: 220, label: "Suche" },
    { x: 180, y: 120, label: "Analyse" },
    { x: 320, y: 200, label: "Draft" },
    { x: 440, y: 90, label: "Review" },
  ];

  return (
    <svg
      viewBox="0 0 480 280"
      className={className}
      aria-hidden="true"
      focusable="false"
    >
      <defs>
        <pattern id="hero-grid" width="40" height="40" patternUnits="userSpaceOnUse">
          <path d="M 40 0 L 0 0 0 40" fill="none" stroke="currentColor" strokeOpacity="0.06" strokeWidth="1" />
        </pattern>
      </defs>
      <rect width="480" height="280" fill="url(#hero-grid)" />

      {nodes.slice(0, -1).map((node, index) => {
        const next = nodes[index + 1];
        return (
          <line
            key={`line-${node.label}`}
            x1={node.x}
            y1={node.y}
            x2={next.x}
            y2={next.y}
            stroke="currentColor"
            strokeOpacity="0.35"
            strokeWidth="1.5"
            strokeDasharray="4 5"
          />
        );
      })}

      {nodes.map((node) => (
        <g key={node.label}>
          <rect
            x={node.x - 10}
            y={node.y - 10}
            width="20"
            height="20"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
          />
          <rect x={node.x - 3} y={node.y - 3} width="6" height="6" fill="currentColor" />
          <text
            x={node.x}
            y={node.y + 30}
            textAnchor="middle"
            fill="currentColor"
            fontSize="11"
            fontFamily="monospace"
            letterSpacing="0.05em"
            opacity="0.6"
          >
            {node.label.toUpperCase()}
          </text>
        </g>
      ))}
    </svg>
  );
}
