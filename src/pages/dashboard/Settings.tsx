import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

const Settings = () => {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">Manage your account, preferences, and subscription.</p>
      </div>

      <Tabs defaultValue="profile" className="space-y-6">
        <TabsList className="bg-muted/50 p-1 rounded-full">
          <TabsTrigger value="profile" className="rounded-full px-6">Profile</TabsTrigger>
          <TabsTrigger value="notifications" className="rounded-full px-6">Notifications</TabsTrigger>
          <TabsTrigger value="billing" className="rounded-full px-6">Billing</TabsTrigger>
          <TabsTrigger value="security" className="rounded-full px-6">Security</TabsTrigger>
        </TabsList>

        <TabsContent value="profile">
          <Card className="border-none shadow-sm">
            <CardHeader>
              <CardTitle className="text-lg font-bold">Profile Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center gap-6 mb-6">
                <div className="w-20 h-20 rounded-full bg-primary/10 flex items-center justify-center border-2 border-dashed border-primary/20">
                  <span className="text-2xl font-bold text-primary">AR</span>
                </div>
                <Button variant="outline" size="sm" className="rounded-full">Change Avatar</Button>
              </div>
              
              <div className="grid sm:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label>Full Name</Label>
                  <Input defaultValue="Alex Rivera" />
                </div>
                <div className="space-y-2">
                  <Label>Email Address</Label>
                  <Input defaultValue="alex@example.com" />
                </div>
                <div className="space-y-2">
                  <Label>Phone Number</Label>
                  <Input defaultValue="+1 (555) 000-0000" />
                </div>
                <div className="space-y-2">
                  <Label>LinkedIn Profile</Label>
                  <Input defaultValue="linkedin.com/in/alexrivera" />
                </div>
              </div>
              
              <div className="flex justify-end pt-4">
                <Button className="rounded-full px-8">Save Changes</Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="notifications">
          <Card className="border-none shadow-sm">
            <CardHeader>
              <CardTitle className="text-lg font-bold">Notification Preferences</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {[
                { title: "New Job Matches", desc: "Get notified when we find a role that matches your profile." },
                { title: "Application Updates", desc: "Receive alerts when an application status changes." },
                { title: "Interview Requests", desc: "Instant notifications for interview invitations." },
                { title: "Weekly Summary", desc: "A weekly report of your job search progress." }
              ].map((item, i) => (
                <div key={i} className="flex items-center justify-between py-4 border-b last:border-0">
                  <div className="space-y-0.5">
                    <p className="font-bold">{item.title}</p>
                    <p className="text-xs text-muted-foreground">{item.desc}</p>
                  </div>
                  <Switch defaultChecked={i < 3} />
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default Settings;