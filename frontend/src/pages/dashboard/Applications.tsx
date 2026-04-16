import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { MoreHorizontal, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";

const applications = [
  { company: "Stripe", role: "Backend Engineer", status: "Interview", date: "Oct 24, 2023", match: 94 },
  { company: "OpenAI", role: "SWE", status: "Applied", date: "Oct 22, 2023", match: 92 },
  { company: "Netflix", role: "ML Engineer", status: "Rejected", date: "Oct 18, 2023", match: 89 },
  { company: "Vercel", role: "Frontend Engineer", status: "Offer", date: "Oct 15, 2023", match: 87 },
  { company: "Google", role: "L5 SWE", status: "Applied", date: "Oct 12, 2023", match: 81 },
];

const statusColors: Record<string, string> = {
  "Applied": "bg-blue-100 text-blue-700 border-blue-200",
  "Interview": "bg-purple-100 text-purple-700 border-purple-200",
  "Rejected": "bg-red-100 text-red-700 border-red-200",
  "Offer": "bg-green-100 text-green-700 border-green-200",
};

const Applications = () => {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Applications</h1>
        <p className="text-muted-foreground">Track the status of all your active and past applications.</p>
      </div>

      <Card className="border-none shadow-sm overflow-hidden">
        <CardContent className="p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-muted-foreground border-b bg-muted/30">
                <th className="text-left p-4 font-medium">Company & Role</th>
                <th className="text-left p-4 font-medium">Status</th>
                <th className="text-left p-4 font-medium">Date Applied</th>
                <th className="text-left p-4 font-medium">Match Score</th>
                <th className="text-right p-4 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {applications.map((app, i) => (
                <tr key={i} className="hover:bg-muted/20 transition-colors">
                  <td className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded bg-muted flex items-center justify-center font-bold text-xs text-muted-foreground">
                        {app.company[0]}
                      </div>
                      <div>
                        <p className="font-bold leading-none mb-1">{app.role}</p>
                        <p className="text-xs text-muted-foreground">{app.company}</p>
                      </div>
                    </div>
                  </td>
                  <td className="p-4">
                    <Badge variant="outline" className={statusColors[app.status]}>
                      {app.status}
                    </Badge>
                  </td>
                  <td className="p-4 text-muted-foreground">{app.date}</td>
                  <td className="p-4">
                    <div className="flex items-center gap-2">
                      <div className="w-12 h-1 bg-muted rounded-full overflow-hidden">
                        <div className="h-full bg-primary" style={{ width: `${app.match}%` }} />
                      </div>
                      <span className="font-bold">{app.match}%</span>
                    </div>
                  </td>
                  <td className="p-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Button variant="ghost" size="icon" className="h-8 w-8">
                        <ExternalLink className="w-4 h-4" />
                      </Button>
                      <Button variant="ghost" size="icon" className="h-8 w-8">
                        <MoreHorizontal className="w-4 h-4" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
};

export default Applications;