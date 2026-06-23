"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { AxiosError } from "axios";

import { Button, Card, Input } from "@/components/ui";
import { useAuth } from "@/hooks/useAuth";
import { ROUTES } from "@/utils/constants";

export default function LoginPage() {
  const router = useRouter();
  const { login, isAuthenticated } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isAuthenticated) router.replace(ROUTES.dashboard);
  }, [isAuthenticated, router]);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
    } catch (err) {
      const msg =
        err instanceof AxiosError
          ? (err.response?.data?.detail ?? "Login failed")
          : "Login failed";
      setError(String(msg));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="p-6">
      <h1 className="mb-1 text-xl font-bold text-fg">Welcome back</h1>
      <p className="mb-5 text-sm text-muted">Sign in to your account</p>
      <form onSubmit={onSubmit} className="space-y-4">
        <Input
          id="email"
          type="email"
          label="Email"
          placeholder="you@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <Input
          id="password"
          type="password"
          label="Password"
          placeholder="••••••••"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        {error && <p className="text-sm text-down">{error}</p>}
        <Button type="submit" loading={loading} className="w-full">
          Sign in
        </Button>
      </form>
      <p className="mt-5 text-center text-sm text-muted">
        No account?{" "}
        <Link href={ROUTES.signup} className="text-brand hover:underline">
          Create one
        </Link>
      </p>
    </Card>
  );
}
