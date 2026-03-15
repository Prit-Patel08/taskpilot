import { Upload, Download, RefreshCw, CheckCircle2, AlertCircle, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

const ResumeAI = () => {
  return (
    <div className="space-y-8">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Resume AI</h1>
          <p className="text-muted-foreground">Optimize your resume for ATS and specific job descriptions.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" className="gap-2 rounded-full">
            <Download className="w-4 h-4" /> Download PDF
          </Button>
          <Button className="gap-2 rounded-full">
            <Upload className="w-4 h-4" /> Replace Resume
          </Button>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-8">
        <Card className="lg:col-span-2 border-none shadow-sm">
          <CardHeader>
            <CardTitle className="text-lg font-bold flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-primary" /> AI Analysis
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-8">
            <div className="grid sm:grid-cols-2 gap-8">
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between mb-2">
                    <span className="text-sm font-medium">ATS Score</span>
                    <span className="text-sm font-bold">84/100</span>
                  </div>
                  <Progress value={84} className="h-2" />
                </div>
                <div>
                  <div className="flex justify-between mb-2">
                    <span className="text-sm font-medium">Keyword Match</span>
                    <span className="text-sm font-bold">72%</span>
                  </div>
                  <Progress value={72} className="h-2" />
                </div>
                <div>
                  <div className="flex justify-between mb-2">
                    <span className="text-sm font-medium">Readability</span>
                    <span className="text-sm font-bold">91%</span>
                  </div>
                  <Progress value={91} className="h-2" />
                </div>
              </div>
              
              <div className="p-6 rounded-2xl bg-primary/5 border border-primary/10">
                <h4 className="font-bold mb-4 text-sm uppercase tracking-wider">Quick Actions</h4>
                <div className="space-y-3">
                  <Button variant="secondary" className="w-full justify-start gap-3 text-sm h-10 rounded-xl">
                    <RefreshCw className="w-4 h-4" /> Generate Tailored Resume
                  </Button>
                  <Button variant="secondary" className="w-full justify-start gap-3 text-sm h-10 rounded-xl">
                    <FileText className="w-4 h-4" /> Generate Cover Letter
                  </Button>
                  <Button variant="secondary" className="w-full justify-start gap-3 text-sm h-10 rounded-xl">
                    <Sparkles className="w-4 h-4" /> Improve Bullet Points
                  </Button>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <h4 className="font-bold text-sm uppercase tracking-wider">Improvement Suggestions</h4>
              <div className="space-y-3">
                {[
                  { type: "success", text: "Strong action verbs used in experience section." },
                  { type: "warning", text: "Missing keywords: 'Kubernetes', 'Microservices', 'CI/CD'." },
                  { type: "warning", text: "Education section could be more concise." },
                  { type: "success", text: "Contact information is clearly visible and formatted." }
                ].map((item, i) => (
                  <div key={i} className="flex items-start gap-3 p-3 rounded-xl border bg-muted/30">
                    {item.type === "success" ? (
                      <CheckCircle2 className="w-5 h-5 text-green-500 mt-0.5" />
                    ) : (
                      <AlertCircle className="w-5 h-5 text-amber-500 mt-0.5" />
                    )}
                    <p className="text-sm">{item.text}</p>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="space-y-8">
          <Card className="border-none shadow-sm">
            <CardHeader>
              <CardTitle className="text-lg font-bold">Skill Gaps</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <p className="text-xs text-muted-foreground">Based on your target roles, consider adding these skills:</p>
                <div className="flex flex-wrap gap-2">
                  {["GraphQL", "Docker", "Terraform", "Redis", "System Design"].map(skill => (
                    <div key={skill} className="px-3 py-1 rounded-full bg-muted text-xs font-medium border">
                      + {skill}
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-none shadow-sm bg-primary text-primary-foreground">
            <CardContent className="p-6">
              <h3 className="font-bold mb-2">Pro Tip</h3>
              <p className="text-sm text-primary-foreground/80 leading-relaxed">
                Tailoring your resume for each application increases your interview chances by 3x. Use our "Generate Tailored Resume" tool for every job you apply to.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

import { FileText } from "lucide-react";
export default ResumeAI;