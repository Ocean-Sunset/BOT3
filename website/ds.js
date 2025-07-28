import Image from "next/image";
import { Button } from "@/components/ui/button"; // Assuming this is shadcn/ui Button

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-[#100018] via-[#1a002a] to-[#080010] text-white font-inter antialiased overflow-hidden">
      {/* Load Inter font using a standard link tag for broader compatibility */}
      <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap" rel="stylesheet" />

      {/* Optional: Background gradient overlay for subtle animation */}
      <div className="absolute inset-0 z-0 opacity-20 animate-pulse-slow">
        <div className="absolute top-0 left-0 w-64 h-64 bg-purple-600 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob"></div>
        <div className="absolute bottom-0 right-0 w-72 h-72 bg-pink-600 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob animation-delay-2000"></div>
      </div>

      {/* Navbar */}
      <nav className="relative z-10 py-6 px-8 flex justify-between items-center max-w-7xl mx-auto">
        <div className="flex items-center space-x-3">
          {/* Using a placeholder for the logo. Replace with your actual image path in public/ */}
          <Image
            src="https://placehold.co/40x40/200040/ffffff?text=EL" // Placeholder for Eobotcat Logo
            width={40}
            height={40}
            alt="Eobotcat Logo"
            className="rounded-full shadow-lg"
          />
          <span className="text-xl font-bold bg-gradient-to-r from-purple-400 via-pink-500 to-orange-400 bg-clip-text text-transparent">
            Eobotcat
          </span>
        </div>
        <div className="space-x-6 hidden md:flex">
          <a href="#features" className="text-purple-300 hover:text-purple-100 transition duration-300">Features</a>
          <a href="#about" className="text-purple-300 hover:text-purple-100 transition duration-300">About</a>
          <a href="#invite" className="text-purple-300 hover:text-purple-100 transition duration-300">Invite</a>
          <a href="#" className="text-purple-300 hover:text-purple-100 transition duration-300">Docs</a>
        </div>
        {/* Mobile menu button (optional, if you want to implement a full mobile nav) */}
        <div className="md:hidden">
          <Button variant="ghost" size="icon" className="text-purple-300 hover:bg-purple-900">
            {/* You'd use an icon here, e.g., from lucide-react */}
            ☰
          </Button>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative z-10 flex flex-col items-center justify-center text-center py-24 px-6 min-h-[calc(100vh-80px)]">
        {/* Using a placeholder for the logo. Replace with your actual image path in public/ */}
        <Image
          src="https://placehold.co/128x128/200040/ffffff?text=Eobotcat+Logo" // Placeholder for Eobotcat Logo
          width={128}
          height={128}
          alt="Eobotcat Logo"
          className="mb-6 drop-shadow-[0_0_20px_rgba(168,85,247,0.7)] animate-fade-in-up"
        />
        <h1 className="text-5xl md:text-7xl font-extrabold bg-gradient-to-r from-purple-400 via-pink-500 to-orange-400 bg-clip-text text-transparent leading-tight animate-fade-in-up animation-delay-300">
          Eobotcat
        </h1>
        <p className="mt-4 text-xl md:text-3xl text-purple-200 max-w-2xl animate-fade-in-up animation-delay-600">
          Where vision meets precision
        </p>
        <Button className="mt-10 px-8 py-4 text-lg bg-purple-700 hover:bg-purple-800 rounded-full shadow-xl transition-all duration-300 transform hover:scale-105 animate-fade-in-up animation-delay-900">
          Invite Eobotcat
        </Button>
      </section>

      {/* Features Section */}
      <section id="features" className="relative z-10 py-20 px-8 max-w-6xl mx-auto">
        <h2 className="text-4xl md:text-5xl font-bold text-center mb-16 text-purple-300 drop-shadow-md">
          What can Eobotcat do?
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-12">
          {/* Feature Card 1: Customization */}
          <div className="bg-purple-950 bg-opacity-40 p-8 rounded-3xl shadow-2xl border border-purple-800 hover:border-pink-500 transition-all duration-300 transform hover:-translate-y-2">
            <div className="text-5xl mb-4 text-pink-400 text-center">✨</div> {/* Icon for Customization */}
            <h3 className="text-2xl font-bold mb-3 text-purple-100 text-center">Customization</h3>
            <p className="text-purple-300 text-lg text-center">Tweak your server’s look, commands, and experience with modular control, making it uniquely yours.</p>
          </div>
          {/* Feature Card 2: Safety */}
          <div className="bg-purple-950 bg-opacity-40 p-8 rounded-3xl shadow-2xl border border-purple-800 hover:border-orange-500 transition-all duration-300 transform hover:-translate-y-2">
            <div className="text-5xl mb-4 text-orange-400 text-center">🛡️</div> {/* Icon for Safety */}
            <h3 className="text-2xl font-bold mb-3 text-purple-100 text-center">Safety</h3>
            <p className="text-purple-300 text-lg text-center">Advanced moderation tools, robust anti-spam measures, and comprehensive user protection features.</p>
          </div>
          {/* Feature Card 3: XP & Levels */}
          <div className="bg-purple-950 bg-opacity-40 p-8 rounded-3xl shadow-2xl border border-purple-800 hover:border-purple-500 transition-all duration-300 transform hover:-translate-y-2">
            <div className="text-5xl mb-4 text-purple-400 text-center">🌟</div> {/* Icon for XP & Levels */}
            <h3 className="text-2xl font-bold mb-3 text-purple-100 text-center">XP & Levels</h3>
            <p className="text-purple-300 text-lg text-center">Engage your community with a dynamic progression system, unlockable roles, and stunning rank-up visuals.</p>
          </div>
        </div>
      </section>

      {/* About Eobotcat Section */}
      <section id="about" className="relative z-10 py-20 px-8 max-w-5xl mx-auto text-center">
        <h2 className="text-4xl md:text-5xl font-bold mb-12 text-pink-300 drop-shadow-md">
          About Eobotcat
        </h2>
        <p className="text-purple-200 text-lg md:text-xl leading-relaxed mb-8">
          Eobotcat is designed to be the ultimate companion for your Discord server. We believe in empowering communities with powerful, intuitive tools that enhance engagement, ensure safety, and provide unparalleled customization. Our mission is to help you build a vibrant and thriving online space.
        </p>
        <p className="text-purple-200 text-lg md:text-xl leading-relaxed">
          From robust moderation capabilities to a rewarding leveling system, Eobotcat brings a new dimension to your server experience. Join the future of Discord bot technology today!
        </p>
      </section>

      {/* Call to Action Section */}
      <section id="invite" className="relative z-10 py-20 px-8 bg-purple-900 bg-opacity-20 rounded-t-3xl shadow-inner-xl text-center">
        <h2 className="text-4xl md:text-5xl font-bold mb-8 text-orange-300 drop-shadow-md">
          Ready to elevate your server?
        </h2>
        <p className="text-purple-200 text-lg md:text-xl max-w-3xl mx-auto mb-10">
          Invite Eobotcat to your Discord server now and unlock a new level of engagement, safety, and customization. It's free, powerful, and built with your community in mind.
        </p>
        <Button className="px-10 py-5 text-xl bg-gradient-to-r from-pink-600 to-purple-700 hover:from-pink-700 hover:to-purple-800 rounded-full shadow-2xl transition-all duration-300 transform hover:scale-105 animate-bounce-subtle">
          🚀 Invite Eobotcat to Your Server
        </Button>
      </section>

      {/* Footer */}
      <footer className="relative z-10 py-10 text-center text-purple-400 text-sm bg-gradient-to-t from-[#080010] to-[#100018] border-t border-purple-900">
        © {new Date().getFullYear()} Eobotcat. Built with precision and passion.
      </footer>

      {/* Custom Styles for animations */}
      <style>{`
        /* Subtle blob animation */
        @keyframes blob {
          0% { transform: translate(0, 0) scale(1); }
          33% { transform: translate(30px, -50px) scale(1.1); }
          66% { transform: translate(-20px, 20px) scale(0.9); }
          100% { transform: translate(0, 0) scale(1); }
        }
        .animate-blob {
          animation: blob 7s infinite cubic-bezier(0.6, 0.01, 0.3, 0.9);
        }
        .animation-delay-2000 {
          animation-delay: 2s;
        }

        /* Pulse slow for background */
        @keyframes pulse-slow {
          0%, 100% { opacity: 0.2; }
          50% { opacity: 0.3; }
        }
        .animate-pulse-slow {
          animation: pulse-slow 15s infinite ease-in-out;
        }

        /* Fade in from bottom */
        @keyframes fade-in-up {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .animate-fade-in-up {
          animation: fade-in-up 0.8s ease-out forwards;
        }
        .animate-fade-in-up.animation-delay-300 { animation-delay: 0.3s; }
        .animate-fade-in-up.animation-delay-600 { animation-delay: 0.6s; }
        .animate-fade-in-up.animation-delay-900 { animation-delay: 0.9s; }

        /* Subtle bounce for CTA button */
        @keyframes bounce-subtle {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-5px); }
        }
        .animate-bounce-subtle {
          animation: bounce-subtle 3s infinite ease-in-out;
        }
      `}</style>
    </main>
  );
}
