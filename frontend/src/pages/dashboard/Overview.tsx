import { 
  Briefcase, 
  Send, 
  Target, 
  Calendar,
  ArrowUpRight,
  MoreHorizontal
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const stats = [
  { label: "Jobs Found Today", value: "124", icon: Briefcase, trend: "+12%" },
  { label: "Applications Sent", value: "42", icon: Send, trend: "+5%" },
  { label: "Avg. Match Score", value: "88%", icon: Target, trend: "+2%" },
  { label: "Upcoming Interviews", value: "3", icon: Calendar, trend: "0" },
];

const recentMatches = [
  { company: "Stripe", role: "Backend Engineer", match: 94, salary: "$180k", location: "Remote" },
  { company: "OpenAI", role: "SWE", match: 92, salary: "$200k", location: "SF" },
  { company: "Netflix", role: "ML Engineer", match: 89, salary: "$190k", location: "Remote" },
  { company: "Vercel", role: "Frontend Engineer", match: 87, salary: "$175k", location: "Remote" },
];

const DashboardOverview = () => {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Welcome back, Alex</h1>
        <p className="text-muted-foreground">Here's what's happening with your job search today.</p>
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, i) => (
          <Card key={i} className="border-none shadow-sm bg-card">
            <CardContent className="p-6">
              <div className="flex justify-between items-start mb-4">
                <div className="p-2 rounded-lg bg-primary/5 text-primary">
                  <stat.icon className="w-5 h-5" />
                </div>
                <span className="text-xs font-medium text-green-600 bg-green-50 px-2 py-1 rounded-full">
                  {stat.trend}
                </span>
              </div>
              <p className="text-sm text-muted-foreground mb-1">{stat.label}</p>
              <h3 className="text-2xl font-bold">{stat.value}</h3>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid lg:grid-cols-3 gap-8">
        <Card className="lg:col-span-2 border-none shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-lg font-bold">Recent Job Matches</CardTitle>
            <Button variant="ghost" size="sm" className="text-xs">View all</Button>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {recentMatches.map((job, i) => (
                <div key={i} className="flex items-center justify-between group">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center font-bold text-muted-foreground">
                      {job.company[0]}
                    </div>
                    <div>
                      <p className="font-bold leading-none mb-1">{job.role}</p>
                      <p className="text-xs text-muted-foreground">{job.company} • {job.location}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-6">
                    <div className="text-right hidden sm:block">
                      <p className="text-sm font-bold">{job.match}%</p>
                      <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Match</p>
                    </div>
                    <Button size="sm" className="rounded-full h-8 px-4 opacity-0 group-hover:opacity-100 transition-opacity">
                      Apply
                    </Button>
                    <Button variant="ghost" size="icon" className="h-8 w-8">
                      <MoreHorizontal className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="border-none shadow-sm">
          <CardHeader>
            <CardTitle className="text-lg font-bold">Activity Feed</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {[
                { title: "Application Sent", desc: "Applied to Senior SWE at Stripe", time: "2h ago" },
                { title: "New Match Found", desc: "Backend Role at OpenAI (92% match)", time: "5h ago" },
                { title: "Resume Optimized", desc: "AI updated your skills section", time: "Yesterday" },
                { title: "Interview Scheduled", desc: "Netflix - Technical Round", time: "2 days ago" }
              ].map((item, i) => (
                <div key={i} className="flex gap-4 relative">
                  {i !== 3 && <div className="absolute left-2 top-6 bottom-0 w-px bg-border" />}
                  <div className="w-4 h-4 rounded-full bg-primary/10 border-2 border-primary mt-1 z-10" />
                  <div>
                    <p className="text-sm font-bold leading-none mb-1">{item.title}</p>
                    <p className="text-xs text-muted-foreground mb-1">{item.desc}</p>
                    <p className="text-[10px] text-muted-foreground uppercase">{item.time}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default DashboardOverview;