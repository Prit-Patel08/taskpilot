import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Bell, Search, User } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

const DashboardLayout = () => {
  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar />
      <div className="flex-grow flex flex-col">
        <header className="h-16 border-b bg-card/50 backdrop-blur-sm sticky top-0 z-10 px-8 flex items-center justify-between">
          <div className="relative w-96">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input 
              placeholder="Search jobs, applications..." 
              className="pl-10 bg-muted/50 border-none h-9 rounded-full focus-visible:ring-1"
            />
          </div>
          
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" className="rounded-full relative">
              <Bell className="w-5 h-5" />
              <span className="absolute top-2 right-2 w-2 h-2 bg-primary rounded-full border-2 border-background" />
            </Button>
            <div className="flex items-center gap-3 pl-4 border-l">
              <div className="text-right hidden sm:block">
                <p className="text-sm font-bold leading-none">Alex Rivera</p>
                <p className="text-xs text-muted-foreground">Pro Plan</p>
              </div>
              <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center border">
                <User className="w-4 h-4" />
              </div>
            </div>
          </div>
        </header>
        
        <main className="p-8 max-w-7xl mx-auto w-full">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default DashboardLayout;