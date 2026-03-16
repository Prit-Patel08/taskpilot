import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  Briefcase,
  Send,
  FileText,
  Zap,
  Settings,
  LogOut,
  CreditCard,
  User,
  BarChart3,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { supabase } from "@/lib/supabaseClient";

const navItems = [
  { icon: LayoutDashboard, label: "Dashboard", path: "/app/dashboard" },
  { icon: Briefcase, label: "Jobs", path: "/app/jobs" },
  { icon: BarChart3, label: "Metrics", path: "/app/metrics" },
  { icon: Send, label: "Applications", path: "/app/applications" },
  { icon: FileText, label: "Resume AI", path: "/app/resume" },
  { icon: Zap, label: "Automation", path: "/app/automation" },
  { icon: Settings, label: "Settings", path: "/app/settings" },
];

export const Sidebar = () => {
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await supabase.auth.signOut();
    navigate("/login", { replace: true });
  };

  return (
    <aside className="w-64 border-r bg-card flex flex-col h-screen sticky top-0">
      <div className="p-6 flex items-center gap-2">
        <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
          <span className="text-primary-foreground font-bold text-xl">T</span>
        </div>
        <span className="text-xl font-bold tracking-tight">TaskPilot</span>
      </div>

      <nav className="flex-grow px-4 space-y-1">
        {navItems.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            className={cn(
              "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
              location.pathname === item.path 
                ? "bg-primary text-primary-foreground" 
                : "text-muted-foreground hover:bg-muted hover:text-foreground"
            )}
          >
            <item.icon className="w-4 h-4" />
            {item.label}
          </Link>
        ))}
      </nav>

      <div className="p-4 border-t space-y-1">
        <Button variant="ghost" className="w-full justify-start gap-3 text-muted-foreground hover:text-foreground px-3">
          <User className="w-4 h-4" /> Profile
        </Button>
        <Button variant="ghost" className="w-full justify-start gap-3 text-muted-foreground hover:text-foreground px-3">
          <CreditCard className="w-4 h-4" /> Billing
        </Button>
        <Button
          variant="ghost"
          className="w-full justify-start gap-3 text-destructive hover:text-destructive hover:bg-destructive/10 px-3"
          onClick={handleLogout}
        >
          <LogOut className="w-4 h-4" /> Logout
        </Button>
      </div>
    </aside>
  );
};
