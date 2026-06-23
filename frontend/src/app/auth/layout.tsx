export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-bg px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex items-center justify-center gap-2">
          <span className="text-2xl">📊</span>
          <span className="text-lg font-bold text-fg">NEPSE&nbsp;AI</span>
        </div>
        {children}
      </div>
    </div>
  );
}
