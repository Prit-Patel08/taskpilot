import { Button } from "@/components/ui/button";
import { Check } from "lucide-react";
import { Link } from "react-router-dom";

export const Pricing = () => {
  return (
    <section id="pricing" className="py-24 px-4 bg-muted/30">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">Simple, transparent pricing</h2>
          <p className="text-muted-foreground">Choose the plan that works best for your career goals.</p>
        </div>
        
        <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          {/* Free Plan */}
          <div className="p-8 rounded-2xl border bg-card flex flex-col">
            <div className="mb-8">
              <h3 className="text-xl font-bold mb-2">Free Plan</h3>
              <div className="flex items-baseline gap-1">
                <span className="text-4xl font-bold">$0</span>
                <span className="text-muted-foreground">/month</span>
              </div>
            </div>
            
            <ul className="space-y-4 mb-8 flex-grow">
              <li className="flex items-center gap-3 text-sm">
                <Check className="w-4 h-4 text-primary" /> 5 applications per month
              </li>
              <li className="flex items-center gap-3 text-sm">
                <Check className="w-4 h-4 text-primary" /> Basic job matching
              </li>
              <li className="flex items-center gap-3 text-sm">
                <Check className="w-4 h-4 text-primary" /> Resume analysis
              </li>
              <li className="flex items-center gap-3 text-sm">
                <Check className="w-4 h-4 text-primary" /> Email support
              </li>
            </ul>
            
            <Link to="/signup" className="w-full">
              <Button variant="outline" className="w-full rounded-full">Get Started</Button>
            </Link>
          </div>
          
          {/* Pro Plan */}
          <div className="p-8 rounded-2xl border-2 border-primary bg-card flex flex-col relative">
            <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-primary text-primary-foreground text-[10px] font-bold uppercase tracking-widest px-3 py-1 rounded-full">
              Most Popular
            </div>
            
            <div className="mb-8">
              <h3 className="text-xl font-bold mb-2">Pro Plan</h3>
              <div className="flex items-baseline gap-1">
                <span className="text-4xl font-bold">$29</span>
                <span className="text-muted-foreground">/month</span>
              </div>
            </div>
            
            <ul className="space-y-4 mb-8 flex-grow">
              <li className="flex items-center gap-3 text-sm">
                <Check className="w-4 h-4 text-primary" /> Unlimited applications
              </li>
              <li className="flex items-center gap-3 text-sm">
                <Check className="w-4 h-4 text-primary" /> Priority AI matching
              </li>
              <li className="flex items-center gap-3 text-sm">
                <Check className="w-4 h-4 text-primary" /> Tailored cover letters
              </li>
              <li className="flex items-center gap-3 text-sm">
                <Check className="w-4 h-4 text-primary" /> ATS optimization
              </li>
              <li className="flex items-center gap-3 text-sm">
                <Check className="w-4 h-4 text-primary" /> Priority support
              </li>
            </ul>
            
            <Link to="/signup" className="w-full">
              <Button className="w-full rounded-full">Start Pro Trial</Button>
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
};