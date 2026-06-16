"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { apiFetch } from "@/lib/api";

interface Balance {
  available: boolean;
  balance: number | null;
  unit: string | null;
  error: string | null;
}

interface ProviderRow {
  name: string;
  vendor: string | null;
  vendor_label: string | null;
  kind: string | null;
  cost_model: string;
  approx_price: string;
  balance: Balance | null;
  assets_generated: number;
}

interface Overview {
  active: {
    image_provider: string;
    image_fallbacks: string[];
    animation_mode: string;
    tier_animation_map: Record<string, string | null>;
  };
  image_providers: ProviderRow[];
  animation_providers: ProviderRow[];
  usage: Record<string, number>;
}

function BalanceCell({ balance }: { balance: Balance | null }) {
  if (!balance) return <span className="text-muted-foreground">—</span>;
  if (balance.available) {
    return (
      <span className="font-medium">
        {balance.balance ?? "?"}{" "}
        <span className="text-xs font-normal text-muted-foreground">
          {balance.unit}
        </span>
      </span>
    );
  }
  return (
    <span className="text-xs text-amber-600 dark:text-amber-400" title={balance.error ?? ""}>
      {balance.error ?? "unavailable"}
    </span>
  );
}

function ProviderTable({
  rows,
  activeName,
  fallbacks,
}: {
  rows: ProviderRow[];
  activeName: string;
  fallbacks?: string[];
}) {
  return (
    <div className="overflow-x-auto rounded-xl border">
      <table className="w-full text-sm">
        <thead className="bg-muted/50 text-left text-xs uppercase text-muted-foreground">
          <tr>
            <th className="px-4 py-2">Provider</th>
            <th className="px-4 py-2">Vendor</th>
            <th className="px-4 py-2">Cost model</th>
            <th className="px-4 py-2">Approx. price</th>
            <th className="px-4 py-2">Balance</th>
            <th className="px-4 py-2 text-right">Generated</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const isActive = r.name === activeName;
            const isFallback = fallbacks?.includes(r.name);
            return (
              <tr key={r.name} className="border-t">
                <td className="px-4 py-2 font-medium">
                  {r.name}
                  {isActive && (
                    <span className="ml-2 rounded-full bg-green-100 px-2 py-0.5 text-[10px] font-semibold text-green-800 dark:bg-green-950 dark:text-green-300">
                      ACTIVE
                    </span>
                  )}
                  {!isActive && isFallback && (
                    <span className="ml-2 rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-semibold text-blue-800 dark:bg-blue-950 dark:text-blue-300">
                      FALLBACK
                    </span>
                  )}
                </td>
                <td className="px-4 py-2 text-muted-foreground">{r.vendor_label ?? "—"}</td>
                <td className="px-4 py-2 text-muted-foreground">{r.cost_model}</td>
                <td className="px-4 py-2 text-muted-foreground">{r.approx_price}</td>
                <td className="px-4 py-2">
                  <BalanceCell balance={r.balance} />
                </td>
                <td className="px-4 py-2 text-right tabular-nums">{r.assets_generated}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default function AdminProvidersPage() {
  const { getToken } = useAuth();
  const [data, setData] = useState<Overview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const token = await getToken();
      const result = await apiFetch<Overview>("/api/v1/admin/providers", {
        token: token ?? undefined,
      });
      setData(result);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load providers overview",
      );
    } finally {
      setLoading(false);
    }
  }, [getToken]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="mx-auto max-w-md py-20 text-center">
        <h2 className="text-xl font-bold">Couldn&apos;t load providers</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          {error || "No data."} (Admin access is restricted to allow-listed emails.)
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl py-8">
      <h1 className="text-2xl font-bold">Providers &amp; Costs</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Live balances, cost models, and how many assets each provider has generated.
      </p>

      <div className="mt-6 rounded-xl border bg-muted/30 p-4 text-sm">
        <div className="flex flex-wrap gap-x-8 gap-y-1">
          <span>
            <span className="text-muted-foreground">Active image: </span>
            <span className="font-medium">{data.active.image_provider}</span>
          </span>
          <span>
            <span className="text-muted-foreground">Image fallbacks: </span>
            <span className="font-medium">
              {data.active.image_fallbacks.length
                ? data.active.image_fallbacks.join(" → ")
                : "none"}
            </span>
          </span>
          <span>
            <span className="text-muted-foreground">Animation mode: </span>
            <span className="font-medium">{data.active.animation_mode}</span>
          </span>
        </div>
        {data.active.animation_mode === "auto" && (
          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
            {Object.entries(data.active.tier_animation_map).map(([tier, prov]) => (
              <span key={tier}>
                {tier} → <span className="font-medium text-foreground">{prov ?? "storyboard"}</span>
              </span>
            ))}
          </div>
        )}
      </div>

      <h2 className="mt-8 mb-3 text-lg font-semibold">Image providers</h2>
      <ProviderTable
        rows={data.image_providers}
        activeName={data.active.image_provider}
        fallbacks={data.active.image_fallbacks}
      />

      <h2 className="mt-8 mb-3 text-lg font-semibold">Animation providers</h2>
      <ProviderTable
        rows={data.animation_providers}
        activeName={
          data.active.animation_mode === "auto" ||
          data.active.animation_mode === "none"
            ? ""
            : data.active.animation_mode
        }
        fallbacks={
          data.active.animation_mode === "auto"
            ? Object.values(data.active.tier_animation_map).filter(
                (v): v is string => !!v,
              )
            : []
        }
      />
      {data.active.animation_mode === "auto" && (
        <p className="mt-2 text-xs text-muted-foreground">
          In <strong>auto</strong> mode, the provider is chosen per episode by tier
          (see mapping above); &ldquo;FALLBACK&rdquo; here marks providers that some
          tier uses.
        </p>
      )}
    </div>
  );
}
