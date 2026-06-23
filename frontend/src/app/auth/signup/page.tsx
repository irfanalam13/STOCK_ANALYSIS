"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { AxiosError } from "axios";

import { Button, Card, Input } from "@/components/ui";
import { useAuth } from "@/hooks/useAuth";
import { ROUTES } from "@/utils/constants";

export default function SignupPage() {
  const { signup } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (password !== confirm) {
      setError("Passwords do not match");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    setLoading(true);
    try {
      await signup({ email, password, role: "trader" });
    } catch (err) {
      const msg =
        err instanceof AxiosError
          ? (err.response?.data?.detail ?? "Sign up failed")
          : "Sign up failed";
      setError(String(msg));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="p-6">
      <h1 className="mb-1 text-xl font-bold text-fg">Create account</h1>
      <p className="mb-5 text-sm text-muted">Start trading on NEPSE AI</p>
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
          placeholder="At least 8 characters"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        <Input
          id="confirm"
          type="password"
          label="Confirm password"
          placeholder="••••••••"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          required
        />
        {error && <p className="text-sm text-down">{error}</p>}
        <Button type="submit" loading={loading} className="w-full">
          Create account
        </Button>
      </form>
      <p className="mt-5 text-center text-sm text-muted">
        Already have an account?{" "}
        <Link href={ROUTES.login} className="text-brand hover:underline">
          Sign in
        </Link>
      </p>
    </Card>
  );
}
