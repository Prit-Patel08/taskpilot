import { 
  Search, 
  Zap, 
  FileText, 
  BarChart3, 
  Bell, 
  Filter 
} from "lucide-react";

const features = [
  {
    icon: <Search className="w-6 h-6" />,
    title: "AI Job Matching",
    description: "Our neural engine scans thousands of listings to find roles that perfectly match your skills and goals."
  },
  {
    icon: <Zap className="w-6 h-6" />,
    title: "Automatic Applications",
    description: "TaskPilot fills out complex application forms and submits them instantly, saving you hundreds of hours."
  },
  {
    icon: <FileText className="w-6 h-6" />,
    title: "Resume Optimization",
    description: "AI-powered suggestions to tailor your resume for every specific job description and beat ATS systems."
  },
  {
    icon: <BarChart3 className="w-6 h-6" />,
    title: "Application Tracker",
    description: "A centralized dashboard to monitor every application status, interview request, and offer in real-time."
  },
  {
    icon: <Bell className="w-6 h-6" />,
    title: "Job Alerts",
    description: "Get instant notifications the moment a relevant job is posted, so you're always the first to apply."
  },
  {
    icon: <Filter className="w-6 h-6" />,
    title: "Smart Filters",
    description: "Fine-tune your search with advanced filters for salary, remote work, tech stack, and company culture."
  }
];

export const Features = () => {
  return (
    <section id="features" className="py-24 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">Everything you need to land your next role</h2>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            Powerful tools designed to automate the tedious parts of the job search.
          </p>
        </div>
        
        <div className="grid md:grid-cols-3 gap-8">
          {features.map((feature, index) => (
            <div key={index} className="p-8 rounded-2xl border bg-card hover:shadow-lg transition-all group">
              <div className="w-12 h-12 rounded-xl bg-primary/5 flex items-center justify-center mb-6 group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                {feature.icon}
              </div>
              <h3 className="text-xl font-semibold mb-3">{feature.title}</h3>
              <p className="text-muted-foreground leading-relaxed">
                {feature.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};