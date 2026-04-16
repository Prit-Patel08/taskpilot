export const SocialProof = () => {
  const companies = ["Google", "Meta", "Amazon", "Netflix", "Stripe", "Vercel"];
  
  return (
    <section className="py-20 border-y bg-muted/30">
      <div className="max-w-7xl mx-auto px-4">
        <p className="text-center text-sm font-medium text-muted-foreground mb-10 uppercase tracking-widest">
          Trusted by students and engineers worldwide
        </p>
        <div className="flex flex-wrap justify-center items-center gap-12 md:gap-20 opacity-50 grayscale">
          {companies.map((company) => (
            <span key={company} className="text-2xl font-bold tracking-tighter text-foreground">
              {company}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
};