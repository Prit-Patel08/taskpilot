import { Search, Filter, MapPin, DollarSign, Briefcase } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const jobs = [
  { company: "Stripe", role: "Backend Engineer", match: 94, salary: "$180k - $220k", location: "Remote", tags: ["Node.js", "Go", "PostgreSQL"] },
  { company: "OpenAI", role: "Software Engineer", match: 92, salary: "$200k - $250k", location: "San Francisco", tags: ["Python", "PyTorch", "Distributed Systems"] },
  { company: "Netflix", role: "ML Engineer", match: 89, salary: "$190k - $240k", location: "Remote", tags: ["Java", "Scala", "Spark"] },
  { company: "Vercel", role: "Frontend Engineer", match: 87, salary: "$170k - $210k", location: "Remote", tags: ["React", "Next.js", "TypeScript"] },
  { company: "Airbnb", role: "Fullstack Developer", match: 85, salary: "$175k - $215k", location: "Remote", tags: ["Ruby", "React", "AWS"] },
  { company: "Linear", role: "Product Engineer", match: 82, salary: "$160k - $200k", location: "Remote", tags: ["TypeScript", "React", "Node.js"] },
];

const Jobs = () => {
  return (
    <div className="space-y-8">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Job Matches</h1>
          <p className="text-muted-foreground">AI-curated roles based on your profile and preferences.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" className="gap-2 rounded-full">
            <Filter className="w-4 h-4" /> Filters
          </Button>
          <Button className="rounded-full">Refresh Matches</Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input placeholder="Role or keyword" className="pl-10 rounded-xl" />
        </div>
        <div className="relative">
          <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input placeholder="Location" className="pl-10 rounded-xl" />
        </div>
        <div className="relative">
          <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input placeholder="Min. Salary" className="pl-10 rounded-xl" />
        </div>
      </div>

      <div className="space-y-4">
        {jobs.map((job, i) => (
          <Card key={i} className="border-none shadow-sm hover:shadow-md transition-shadow group overflow-hidden">
            <CardContent className="p-0">
              <div className="flex flex-col md:flex-row">
                <div className="w-2 bg-primary" />
                <div className="flex-grow p-6 flex flex-col md:flex-row md:items-center justify-between gap-6">
                  <div className="flex items-start gap-4">
                    <div className="w-12 h-12 rounded-xl bg-muted flex items-center justify-center font-bold text-xl text-muted-foreground">
                      {job.company[0]}
                    </div>
                    <div>
                      <h3 className="text-lg font-bold mb-1 group-hover:text-primary transition-colors">{job.role}</h3>
                      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-muted-foreground">
                        <span className="flex items-center gap-1.5"><Briefcase className="w-3.5 h-3.5" /> {job.company}</span>
                        <span className="flex items-center gap-1.5"><MapPin className="w-3.5 h-3.5" /> {job.location}</span>
                        <span className="flex items-center gap-1.5"><DollarSign className="w-3.5 h-3.5" /> {job.salary}</span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex flex-wrap items-center gap-4">
                    <div className="flex gap-2">
                      {job.tags.map(tag => (
                        <Badge key={tag} variant="secondary" className="rounded-full font-normal text-[10px] uppercase tracking-wider">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                    <div className="flex items-center gap-6 pl-6 border-l">
                      <div className="text-center">
                        <p className="text-xl font-bold leading-none">{job.match}%</p>
                        <p className="text-[10px] text-muted-foreground uppercase tracking-widest">Match</p>
                      </div>
                      <Button className="rounded-full px-6">Apply</Button>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
};

export default Jobs;