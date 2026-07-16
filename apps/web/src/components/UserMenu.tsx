"use client";

import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

export function UserMenu() {
  const { user, loading, logout } = useAuth();
  const router = useRouter();

  if (loading) return <div className="h-8 w-20 rounded bg-panel2 animate-pulse" />;
  if (!user)
    return (
      <a href="/login" className="btn-primary text-xs">
        Sign in
      </a>
    );

  async function signOut() {
    await logout();
    router.push("/login");
  }

  return (
    <div className="flex items-center gap-3">
      <a href="/" className="text-sm text-muted hover:text-gray-200">
        Repos
      </a>
      <a href="/discovery" className="text-sm text-muted hover:text-gray-200">
        Discover
      </a>
      <a href="/settings" className="text-sm text-muted hover:text-gray-200">
        Settings
      </a>
      <div className="flex items-center gap-2">
        {user.avatar_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={user.avatar_url}
            alt=""
            className="h-7 w-7 rounded-full border border-border"
          />
        ) : (
          <div className="h-7 w-7 rounded-full bg-gradient-to-br from-accent to-accent2" />
        )}
        <span className="text-sm">{user.login}</span>
      </div>
      <button onClick={signOut} className="text-sm text-muted hover:text-red-300">
        Sign out
      </button>
    </div>
  );
}
