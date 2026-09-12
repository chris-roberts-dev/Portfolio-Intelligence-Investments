import { Route, Routes } from "react-router";

function FoundationPage() {
  return (
    <main className="min-h-screen bg-slate-950 px-6 py-16 text-slate-100">
      <section className="mx-auto max-w-3xl rounded-2xl border border-slate-800 bg-slate-900 p-8 shadow-xl">
        <p className="mb-3 text-sm font-semibold uppercase tracking-[0.2em] text-slate-400">
          Phase 1 foundation
        </p>

        <h1 className="text-4xl font-semibold tracking-tight">
          Portfolio Intelligence
        </h1>

        <p className="mt-4 max-w-2xl text-base leading-7 text-slate-300">
          The frontend platform shell is running. Financial workflows and
          analytics are intentionally deferred to later implementation phases.
        </p>
      </section>
    </main>
  );
}

export function App() {
  return (
    <Routes>
      <Route path="/" element={<FoundationPage />} />
    </Routes>
  );
}