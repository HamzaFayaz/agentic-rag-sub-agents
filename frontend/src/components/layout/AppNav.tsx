import { NavLink } from "react-router-dom";

import { cn } from "@/lib/utils";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  cn(
    "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
    isActive
      ? "bg-slate-100 text-slate-900"
      : "text-slate-600 hover:bg-slate-50 hover:text-slate-900",
  );

export function AppNav() {
  return (
    <nav className="flex items-center gap-1">
      <NavLink to="/" end className={linkClass}>
        Chat
      </NavLink>
      <NavLink to="/documents" className={linkClass}>
        Documents
      </NavLink>
    </nav>
  );
}
