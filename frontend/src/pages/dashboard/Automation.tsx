import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Zap, Shield, Settings2 } from "lucide-react";

const Automation = () => {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Automation</h1>
        <p className="text-muted-foreground">Configure how TaskPilot applies to jobs on your behalf.</p>
      </div>

      <div className="grid lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-8">
          <Card className="border-none shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between">
              <div className="space-y-1">
                <CardTitle className="text-lg font-bold flex items-center gap-2">
                  <Zap className="w-5 h-5 text-primary" /> Auto-Apply Status
                </CardTitle>
                <p className="text-xs text-muted-foreground">Enable or disable automatic applications.</p>
              </div>
              <Switch defaultChecked />
            </CardHeader>
            <CardContent>
              <div className="p-4 rounded-2xl bg-green-50 border border-green-100 flex items-center gap-4">
                <div className="w-10 h-10 rounded-full bg-green-500 flex items-center justify-center text-white">
                  <Shield className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-sm font-bold text-green-900">Agent is Active</p>
                  <p className="text-xs text-green-700">TaskPilot is currently scanning and applying to jobs.</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-none shadow-sm">
            <CardHeader>
              <CardTitle className="text-lg font-bold flex items-center gap-2">
                <Settings2 className="w-5 h-5 text-primary" /> Application Preferences
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid sm:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label>Preferred Roles</Label>
                  <Input placeholder="e.g. Backend Engineer, SWE" defaultValue="Backend Engineer, Fullstack" />
                </div>
                <div className="space-y-2">
                  <Label>Preferred Locations</Label>
                  <Input placeholder="e.g. Remote, SF, NYC" defaultValue="Remote, San Francisco" />
                </div>
                <div className="space-y-2">
                  <Label>Min. Salary (Annual)</Label>
                  <Input placeholder="e.g. 150000" defaultValue="180000" />
                </div>
                <div className="space-y-2">
                  <Label>Experience Level</Label>
                  <Input placeholder="e.g. Senior, Mid" defaultValue="Senior" />
                </div>
              </div>
              
              <div className="space-y-4 pt-4 border-t">
                <div className="flex justify-between items-center">
                  <Label>Max Applications per Day</Label>
                  <span className="text-sm font-bold">20</span>
                </div>
                <Slider defaultValue={[20]} max={50} step={1} />
                <p className="text-[10px] text-muted-foreground">We recommend 15-25 applications per day for optimal results.</p>
              </div>

              <div className="flex justify-end">
                <Button className="rounded-full px-8">Save Preferences</Button>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-8">
          <Card className="border-none shadow-sm">
            <CardHeader>
              <CardTitle className="text-lg font-bold">Automation Stats</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Total Applied</span>
                <span className="font-bold">142</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Success Rate</span>
                <span className="font-bold">98.2%</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Time Saved</span>
                <span className="font-bold">48h</span>
              </div>
              <div className="pt-4 border-t">
                <p className="text-xs text-muted-foreground mb-4">Last application sent 2 hours ago to Stripe.</p>
                <Button variant="outline" className="w-full rounded-full text-xs h-9">View Activity Log</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default Automation;