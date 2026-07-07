export function RayBackground() {
  return (
    <div className="fixed inset-0 w-full h-full pointer-events-none overflow-hidden -z-10">
      <div className="absolute left-1/2 -translate-x-1/2 w-[4000px] sm:w-[6000px] h-[1800px]"
        style={{
          background: 'radial-gradient(circle at center 800px, rgba(59,130,246,0.15) 0%, rgba(59,130,246,0.06) 14%, rgba(59,130,246,0.03) 18%, transparent 22%, transparent 25%)'
        }}
      />
      <div className="absolute top-[175px] sm:top-1/2 left-1/2 w-[1600px] sm:w-[3043px] h-[1600px] sm:h-[2865px] -translate-x-1/2 rotate-180">
        {[
          { border: '12px solid white', mt: '-10px', z: 5 },
          { border: '18px solid #dbeafe', mt: '-8px', z: 4 },
          { border: '18px solid #bfdbfe', mt: '-6px', z: 3 },
          { border: '18px solid #93bbfc', mt: '-3px', z: 2 },
          { border: '16px solid #3b82f6', mt: '0', z: 1, shadow: '0 -10px 20px rgba(59,130,246,0.3)' },
        ].map((ring, i) => (
          <div
            key={i}
            className="absolute inset-0 rounded-full bg-white"
            style={{
              border: ring.border,
              marginTop: ring.mt,
              zIndex: ring.z,
              boxShadow: 'shadow' in ring ? (ring as { shadow?: string }).shadow : undefined,
            }}
          />
        ))}
      </div>
    </div>
  );
}
