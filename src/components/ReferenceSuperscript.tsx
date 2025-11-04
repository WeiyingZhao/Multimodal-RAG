import { cn } from "@/lib/utils";

interface ReferenceSuperscriptProps {
  number: string;
  onClick: () => void;
  className?: string;
}

export function ReferenceSuperscript({ number, onClick, className }: ReferenceSuperscriptProps) {
  return (
    <sup
      className={cn(
        "inline-flex items-center justify-center w-5 h-5 text-xs bg-blue-500 text-white rounded-full cursor-pointer hover:bg-blue-600 transition-colors ml-0.5 mr-0.5",
        "hover:shadow-md hover:scale-105 transform transition-all duration-200",
        className
      )}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick();
        }
      }}
    >
      {number}
    </sup>
  );
}