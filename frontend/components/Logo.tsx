export function LogoMark({ className = "h-8 w-8" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 32 32"
      fill="none"
      className={className}
      xmlns="http://www.w3.org/2000/svg"
    >
      <rect x="0.5" y="0.5" width="31" height="31" rx="8" className="fill-black dark:fill-white" />
      <path
        d="M7 20.5L12.5 14.5L16.5 18L25 8"
        stroke="currentColor"
        className="text-white dark:text-black"
        strokeWidth="2.25"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M19 8H25V14"
        stroke="currentColor"
        className="text-white dark:text-black"
        strokeWidth="2.25"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function Logo({ size = "md" }: { size?: "sm" | "md" | "lg" }) {
  const markSize = size === "lg" ? "h-10 w-10" : size === "sm" ? "h-6 w-6" : "h-8 w-8";
  const textSize = size === "lg" ? "text-2xl" : size === "sm" ? "text-base" : "text-xl";

  return (
    <div className="flex items-center gap-2.5">
      <LogoMark className={markSize} />
      <span className={`${textSize} font-semibold tracking-tight text-black dark:text-zinc-50`}>
        Plutus<span className="font-normal text-zinc-500 dark:text-zinc-400">AI</span>
      </span>
    </div>
  );
}
