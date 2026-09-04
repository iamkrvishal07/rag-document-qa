function Header() {
  return (
    <header className="app-header">
      <div className="mx-auto flex max-w-375 items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-3">
          <div className="brand-logo">
            ✦
          </div>

          <div>
            <h1 className="text-base font-bold tracking-tight text-slate-900">
              DocQuery
            </h1>

            <p className="text-[11px] text-slate-500">
              AI Document Q&A
            </p>
          </div>
        </div>

        <div className="session-pill">
          <span className="session-dot" />
          Session active
        </div>
      </div>
    </header>
  );
}

export default Header;