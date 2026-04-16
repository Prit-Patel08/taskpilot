import { Navbar } from "@/components/landing/Navbar";
import { Hero } from "@/components/landing/Hero";
import { SocialProof } from "@/components/landing/SocialProof";
import { Features } from "@/components/landing/Features";
import { Pricing } from "@/components/landing/Pricing";
import { Footer } from "@/components/landing/Footer";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";

const Index = () => {
  return (
    <div className="min-h-screen bg-background selection:bg-primary/10">
      <Navbar />
      <main>
        <Hero />
        <SocialProof />
        
        {/* How It Works Section */}
        <section id="how-it-works" className="py-24 px-4">
          <div className="max-w-7xl mx-auto">
            <div className="text-center mb-16">
              <h2 className="text-3xl md:text-4xl font-bold mb-4">How TaskPilot works</h2>
              <p className="text-muted-foreground">Three simple steps to automate your career growth.</p>
            </div>
            
            <div className="grid md:grid-cols-3 gap-12">
              {[
                { step: "01", title: "Upload Resume", desc: "Upload your current resume and our AI will analyze your skills and experience." },
                { step: "02", title: "AI Finds Jobs", desc: "Our agent scans thousands of listings to find roles that match your profile perfectly." },
                { step: "03", title: "Apply Automatically", desc: "TaskPilot fills out forms and submits applications on your behalf, 24/7." }
              ].map((item, i) => (
                <div key={i} className="relative">
                  <div className="text-6xl font-black text-muted/20 mb-4">{item.step}</div>
                  <h3 className="text-xl font-bold mb-2">{item.title}</h3>
                  <p className="text-muted-foreground">{item.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <Features />
        
        {/* Product Preview Section */}
        <section className="py-24 px-4 bg-muted/30">
          <div className="max-w-7xl mx-auto">
            <div className="grid lg:grid-cols-2 gap-16 items-center">
              <div>
                <h2 className="text-3xl md:text-4xl font-bold mb-6">Powerful dashboard to track your progress</h2>
                <p className="text-muted-foreground mb-8 leading-relaxed">
                  Monitor every application, match score, and interview request in one place. Our AI provides deep insights into why you're a match for specific roles.
                </p>
                <div className="space-y-4">
                  {[
                    "Real-time match score analysis",
                    "Automated status tracking",
                    "Direct interview scheduling",
                    "Salary benchmark insights"
                  ].map((item, i) => (
                    <div key={i} className="flex items-center gap-3">
                      <div className="w-5 h-5 rounded-full bg-primary/10 flex items-center justify-center">
                        <div className="w-2 h-2 rounded-full bg-primary" />
                      </div>
                      <span className="font-medium">{item}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="rounded-2xl border bg-card shadow-xl overflow-hidden">
                <div className="p-4 border-b bg-muted/50 flex items-center gap-2">
                  <div className="flex gap-1.5">
                    <div className="w-3 h-3 rounded-full bg-red-500/20" />
                    <div className="w-3 h-3 rounded-full bg-yellow-500/20" />
                    <div className="w-3 h-3 rounded-full bg-green-500/20" />
                  </div>
                  <div className="h-4 w-32 bg-muted rounded mx-auto" />
                </div>
                <div className="p-6">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-muted-foreground border-b">
                        <th className="text-left pb-4 font-medium">Company</th>
                        <th className="text-left pb-4 font-medium">Role</th>
                        <th className="text-left pb-4 font-medium">Match</th>
                        <th className="text-right pb-4 font-medium">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {[
                        { company: "Stripe", role: "Backend Engineer", match: 94, status: "Apply" },
                        { company: "OpenAI", role: "SWE", match: 92, status: "Applied" },
                        { company: "Netflix", role: "ML Engineer", match: 89, status: "Apply" }
                      ].map((job, i) => (
                        <tr key={i}>
                          <td className="py-4 font-semibold">{job.company}</td>
                          <td className="py-4 text-muted-foreground">{job.role}</td>
                          <td className="py-4">
                            <div className="flex items-center gap-2">
                              <div className="w-16 h-1.5 bg-muted rounded-full overflow-hidden">
                                <div className="h-full bg-primary" style={{ width: `${job.match}%` }} />
                              </div>
                              <span className="font-bold">{job.match}%</span>
                            </div>
                          </td>
                          <td className="py-4 text-right">
                            <Button size="sm" variant={job.status === "Applied" ? "secondary" : "default"} className="h-8 px-4 rounded-full text-xs">
                              {job.status}
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </section>

        <Pricing />

        {/* Final CTA */}
        <section className="py-24 px-4">
          <div className="max-w-4xl mx-auto text-center bg-primary text-primary-foreground rounded-3xl p-12 md:p-20 relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-full bg-[radial-gradient(circle_at_top_right,rgba(255,255,255,0.1),transparent)]" />
            <h2 className="text-3xl md:text-5xl font-bold mb-6 relative z-10">Let AI handle your job search.</h2>
            <p className="text-primary-foreground/80 mb-10 text-lg max-w-xl mx-auto relative z-10">
              Join thousands of professionals who have automated their career growth with TaskPilot.
            </p>
            <Link to="/signup" className="relative z-10">
              <Button size="lg" variant="secondary" className="rounded-full px-10 h-14 text-lg font-bold">
                Start Applying with AI
              </Button>
            </Link>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
};

export default Index;