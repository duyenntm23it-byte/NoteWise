import { BookOpen, MessageSquare, Upload } from "lucide-react";

function App() {
  return (
    <main className="min-h-screen bg-slate-950 px-6 py-10 text-slate-100">
      <div className="mx-auto max-w-5xl">
        <header className="mb-12 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-amber-400 p-2 text-slate-950">
              <BookOpen size={22} />
            </div>
            <span className="text-xl font-semibold tracking-tight">NoteWise</span>
          </div>
          <span className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-400">
            Personal learning workspace
          </span>
        </header>

        <section className="grid gap-10 md:grid-cols-[1.2fr_0.8fr] md:items-end">
          <div>
            <p className="mb-4 text-sm font-medium uppercase tracking-[0.2em] text-amber-300">
              Learn from your lectures
            </p>
            <h1 className="max-w-2xl text-5xl font-semibold leading-tight tracking-tight">
              Turn lecture files into a conversation.
            </h1>
            <p className="mt-5 max-w-xl text-lg leading-8 text-slate-400">
              Upload your PDF or PPTX, then ask questions grounded in your own course material.
            </p>
          </div>
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl shadow-black/20">
            <div className="mb-6 flex items-center gap-3">
              <MessageSquare className="text-amber-300" size={20} />
              <span className="font-medium">Start a study session</span>
            </div>
            <button className="flex w-full items-center justify-center gap-2 rounded-xl bg-amber-400 px-4 py-3 font-semibold text-slate-950 transition hover:bg-amber-300">
              <Upload size={18} />
              Upload lecture material
            </button>
            <p className="mt-3 text-center text-xs text-slate-500">PDF and PPTX are supported</p>
          </div>
        </section>
      </div>
    </main>
  );
}

export default App;
