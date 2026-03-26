"use client";

import Link from "next/link";
import { SignedIn, SignedOut, UserButton } from "@clerk/nextjs";
import { Button } from "@/components/ui/button";

export function Nav() {
  return (
    <header className="sticky top-0 z-50 border-b border-border/50 bg-background/80 backdrop-blur-lg">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Link href="/" className="text-lg font-bold tracking-tight">
          scooby
        </Link>
        <div className="flex items-center gap-3">
          <SignedOut>
            <Link href="/sign-in">
              <Button size="sm">Sign In</Button>
            </Link>
          </SignedOut>
          <SignedIn>
            <Link href="/stories">
              <Button variant="ghost" size="sm">
                My Stories
              </Button>
            </Link>
            <UserButton />
          </SignedIn>
        </div>
      </div>
    </header>
  );
}
