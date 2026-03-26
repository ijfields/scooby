"use client";

import Link from "next/link";
import { useAuth, UserButton, SignInButton } from "@clerk/nextjs";
import { Button } from "@/components/ui/button";

export function Nav() {
  const { isSignedIn } = useAuth();

  return (
    <header className="sticky top-0 z-50 border-b border-border/50 bg-background/80 backdrop-blur-lg">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Link href="/" className="text-lg font-bold tracking-tight">
          scooby
        </Link>
        <div className="flex items-center gap-3">
          {!isSignedIn && (
            <SignInButton>
              <Button size="sm">Sign In</Button>
            </SignInButton>
          )}
          {isSignedIn && (
            <>
              <Link href="/stories">
                <Button variant="ghost" size="sm">
                  My Stories
                </Button>
              </Link>
              <UserButton />
            </>
          )}
        </div>
      </div>
    </header>
  );
}
