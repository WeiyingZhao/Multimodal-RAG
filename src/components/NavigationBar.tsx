import { Button } from "./ui/button";
import { Moon, Sun } from "lucide-react";
import { useTheme } from "./theme-provider";
import logoImage from "../assets/logo.png";

// interface NavigationBarProps {}

export function NavigationBar() {
  const { theme, setTheme } = useTheme();
  
  return (
    <nav className="h-16 bg-background/95 backdrop-blur-lg border-b border-border flex items-center justify-between px-6 relative z-50">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-gradient-to-br from-gray-700 to-gray-800 dark:from-gray-200 dark:to-gray-300 rounded-lg flex items-center justify-center shadow-lg overflow-hidden">
          <img src={logoImage} alt="Logo" className="w-full h-full object-cover rounded-lg" />
        </div>
        <div>
          <h1 className="text-lg font-medium text-foreground">
            {/* 体验课 */}
          </h1>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <Button
          variant="outline"
          size="icon"
          onClick={() => setTheme(theme === "light" ? "dark" : "light")}
          className="w-9 h-9"
        >
          <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
          <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
        </Button>
        
      </div>
    </nav>
  );
}
