interface LiveWaveformProps {
  active: boolean;
  speaking: boolean;
}

export function LiveWaveform({ active, speaking }: LiveWaveformProps) {
  const heights = active ? (speaking ? [18, 30, 14, 28, 20, 32, 16, 24] : [10, 18, 12, 22, 14, 20, 10, 16]) : [6, 6, 6, 6, 6, 6, 6, 6];
  return (
    <div aria-hidden="true" style={{ display: "inline-flex", alignItems: "center", gap: 3, height: 34 }}>
      {heights.map((h, i) => (
        <span
          key={i}
          style={{
            width: 4,
            height: h,
            borderRadius: 99,
            background: speaking ? "var(--accent)" : active ? "var(--emerald)" : "var(--border)",
            transition: "height 160ms ease",
          }}
        />
      ))}
    </div>
  );
}
