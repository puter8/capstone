"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";

import { AppFrame } from "@/components/v2/AppFrame";
import { Button } from "@/components/v2/Button";
import { IconCard, IconChevronRight, IconReceipt, IconSparkles, IconSpinner } from "@/components/v2/icons";
import { PlanCard, recurringLabel } from "@/components/v2/PlanCard";
import { Sheet } from "@/components/v2/Sheet";
import { Toast } from "@/components/v2/Toast";
import { TopBar } from "@/components/v2/TopBar";
import { pallyApi, PallyApiError } from "@/lib/api";
import type { BillingHistoryEntry, BillingOverviewResponse, BillingProduct } from "@/lib/api";
import { clearUserRouteData, getCurrentUserId, invalidateSubscription, invalidateUsage } from "@/lib/api/route-data";
import {
  canStartCheckout, checkoutBlockMessage, firstCharge, formatBillingDate,
  formatWon, hasBillingAccess, historyLabel, planName, renewalDisclosure, validatedCheckoutUrl,
} from "@/lib/billing-view";
import { supabase } from "@/lib/supabase/client";
import { routes } from "@/lib/v2/routes";
import { cn } from "@/lib/utils";

type BillingData = { products: BillingProduct[]; overview: BillingOverviewResponse };
type SheetKind = { kind: "checkout" } | { kind: "cancel" } | { kind: "cancel-complete" } | { kind: "history"; entry: BillingHistoryEntry } | null;

const WORDMARK_STYLE = { fontVariationSettings: '"SOFT" 0, "WONK" 1' } as const;

function FactRow({ label, children, emphasis = false }: { label: string; children: ReactNode; emphasis?: boolean }) {
  return (
    <div className="flex items-center gap-p-3">
      <dt className="min-w-0 flex-1 text-p-small text-p-text-muted">{label}</dt>
      <dd className={cn("whitespace-nowrap text-p-text", emphasis ? "text-p-card tracking-[-0.02em]" : "text-p-label")}>{children}</dd>
    </div>
  );
}

function SectionTitle({ children, trailing }: { children: ReactNode; trailing?: ReactNode }) {
  return (
    <div className="flex items-center gap-p-3">
      <h2 className="flex-1 text-p-card tracking-[-0.02em] text-p-text">{children}</h2>
      {trailing}
    </div>
  );
}

export default function PlansV2Page() {
  const router = useRouter();
  const [data, setData] = useState<BillingData | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sheetError, setSheetError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [sheet, setSheet] = useState<SheetKind>(null);
  const locked = useRef(false);
  const mounted = useRef(false);
  const requestId = useRef(0);
  const userIdRef = useRef<string | null>(null);
  const authGeneration = useRef(0);
  const authInvalidated = useRef(false);
  const departingForCheckout = useRef(false);

  const clearBillingSession = useCallback(() => {
    authGeneration.current += 1;
    authInvalidated.current = true;
    requestId.current += 1;
    if (userIdRef.current) clearUserRouteData(userIdRef.current);
    userIdRef.current = null;
    locked.current = false;
    departingForCheckout.current = false;
    setData(null);
    setSelectedId(null);
    setSheet(null);
    setSheetError(null);
    setNotice(null);
    setError(null);
    setBusy(false);
    setLoading(false);
    router.replace(routes.login);
  }, [router]);

  const isCurrentSession = useCallback((generation: number) => (
    mounted.current && !authInvalidated.current && generation === authGeneration.current
  ), []);

  useEffect(() => {
    const { data: listener } = supabase.auth.onAuthStateChange((event, session) => {
      if (authInvalidated.current) return;
      const nextUserId = session?.user.id ?? null;
      if (event === "SIGNED_OUT" || (userIdRef.current !== null && nextUserId !== userIdRef.current)) {
        clearBillingSession();
        return;
      }
      userIdRef.current = nextUserId;
    });
    return () => listener.subscription.unsubscribe();
  }, [clearBillingSession]);

  const handleError = useCallback((caught: unknown, inSheet = false) => {
    if (!mounted.current || authInvalidated.current) return;
    if (caught instanceof PallyApiError && caught.code === "unauthorized") {
      clearBillingSession();
      return;
    }
    const message = caught instanceof Error ? caught.message : "결제 정보를 불러오지 못했어요. 다시 시도해 주세요.";
    if (mounted.current) (inSheet ? setSheetError : setError)(message);
  }, [clearBillingSession]);

  const loadData = useCallback(async (reconcile = false): Promise<BillingData | null> => {
    const generation = authGeneration.current;
    const id = ++requestId.current;
    if (!isCurrentSession(generation)) return null;
    const userId = await getCurrentUserId();
    if (!isCurrentSession(generation) || id !== requestId.current) return null;
    if (userIdRef.current !== null && userIdRef.current !== userId) {
      clearBillingSession();
      return null;
    }
    userIdRef.current = userId;
    if (reconcile) await pallyApi.refreshSubscription(userId);
    if (!isCurrentSession(generation) || id !== requestId.current) return null;
    const [catalog, overview] = await Promise.all([pallyApi.getBillingProducts(), pallyApi.getBillingOverview()]);
    if (!isCurrentSession(generation) || id !== requestId.current || userIdRef.current !== userId) return null;
    const next = { products: catalog.products, overview };
    invalidateSubscription(userId);
    invalidateUsage(userId);
    if (mounted.current && id === requestId.current) {
      setData(next);
      setSelectedId((current) => catalog.products.some((product) => product.id === current)
        ? current : (catalog.products.find((product) => product.interval === "year")?.id ?? catalog.products[0]?.id ?? null));
    }
    return next;
  }, [clearBillingSession, isCurrentSession]);

  useEffect(() => {
    let active = true;
    mounted.current = true;
    const generation = authGeneration.current;
    const checkout = new URLSearchParams(window.location.search).get("checkout");
    void loadData(checkout === "success" || checkout === "pending")
      .then((next) => {
        if (!active || !next || !isCurrentSession(generation)) return;
        if (checkout === "cancel") {
          setNotice("결제창을 닫았어요. 아래에서 현재 결제 상태를 확인해 주세요.");
        }
        if (["success", "pending", "cancel"].includes(checkout ?? "")) {
          window.history.replaceState(window.history.state, "", window.location.pathname);
        }
      })
      .catch((caught: unknown) => { if (active && isCurrentSession(generation)) handleError(caught); })
      .finally(() => { if (active && isCurrentSession(generation)) setLoading(false); });
    return () => { active = false; mounted.current = false; requestId.current += 1; };
  }, [handleError, isCurrentSession, loadData]);

  const refresh = useCallback(async (reconcile = true) => {
    const generation = authGeneration.current;
    if (locked.current || !isCurrentSession(generation)) return;
    locked.current = true;
    setBusy(true);
    setError(null);
    setNotice(null);
    try { await loadData(reconcile); }
    catch (caught) { if (isCurrentSession(generation)) handleError(caught); }
    finally { if (isCurrentSession(generation)) { locked.current = false; setBusy(false); setLoading(false); } }
  }, [handleError, isCurrentSession, loadData]);

  useEffect(() => {
    const restore = (event: PageTransitionEvent) => {
      if (!event.persisted && !departingForCheckout.current) return;
      departingForCheckout.current = false;
      locked.current = false;
      setBusy(false);
      setSheet(null);
      setSheetError(null);
      void refresh(false);
    };
    window.addEventListener("pageshow", restore);
    return () => window.removeEventListener("pageshow", restore);
  }, [refresh]);

  useEffect(() => {
    const end = data?.overview.subscription.current_period_end;
    if (!end || !data.overview.subscription.entitled) return;
    const delay = new Date(end).getTime() - Date.now();
    if (delay <= 0 || delay > 2_147_000_000) return;
    const timer = window.setTimeout(() => { void refresh(false); }, delay + 100);
    return () => window.clearTimeout(timer);
  }, [data, refresh]);

  const closeSheet = () => { if (!locked.current || sheet?.kind === "cancel-complete") { setSheet(null); setSheetError(null); } };
  const selected = data?.products.find((product) => product.id === selectedId);
  const overview = data?.overview;
  const subscription = overview?.subscription;
  const entitled = subscription ? hasBillingAccess(subscription) : false;
  const currentProduct = data?.products.find((product) => product.id === subscription?.product_id);
  const pending = overview?.pending_order;
  const purchasable = overview ? canStartCheckout(overview) : false;

  const openCheckout = async () => {
    const generation = authGeneration.current;
    if (locked.current || !selected || !purchasable || !isCurrentSession(generation)) return;
    locked.current = true;
    setBusy(true);
    setSheetError(null);
    setError(null);
    setSheet({ kind: "checkout" });
    try {
      const next = await loadData();
      if (!next || !isCurrentSession(generation)) return;
      if (!canStartCheckout(next.overview)) {
        setSheet(null);
        setError(checkoutBlockMessage(next.overview));
      }
    } catch (caught) { if (isCurrentSession(generation)) handleError(caught, true); }
    finally { if (isCurrentSession(generation)) { locked.current = false; setBusy(false); } }
  };

  const startCheckout = async () => {
    const generation = authGeneration.current;
    if (locked.current || !selected || !purchasable || sheetError || !isCurrentSession(generation)) return;
    locked.current = true;
    setBusy(true);
    setSheetError(null);
    try {
      const userId = await getCurrentUserId();
      if (!isCurrentSession(generation)) return;
      if (userId !== userIdRef.current) { clearBillingSession(); return; }
      const returnUrl = `${window.location.origin}${routes.plans}`;
      const response = await pallyApi.createCheckout({
        product_id: selected.id,
        success_url: `${returnUrl}?checkout=success`,
        cancel_url: `${returnUrl}?checkout=cancel`,
        mobile: /Android|iPhone|iPad|iPod/i.test(navigator.userAgent),
      }, userId);
      if (!isCurrentSession(generation)) return;
      if (response.checkout.product_id !== selected.id) throw new Error("선택한 요금제와 결제 정보가 달라요. 다시 시도해 주세요.");
      const url = validatedCheckoutUrl(response.checkout.checkout_url);
      departingForCheckout.current = true;
      window.location.assign(url);
      // Keep the lock until navigation finishes so another click cannot create an order.
    } catch (caught) {
      if (!isCurrentSession(generation)) return;
      handleError(caught, true);
      locked.current = false;
      if (mounted.current) setBusy(false);
    }
  };

  const stopRenewal = async () => {
    const generation = authGeneration.current;
    if (locked.current || !subscription?.will_renew || !isCurrentSession(generation)) return;
    locked.current = true;
    setBusy(true);
    setSheetError(null);
    try {
      const userId = await getCurrentUserId();
      if (!isCurrentSession(generation)) return;
      if (userId !== userIdRef.current) { clearBillingSession(); return; }
      const response = await pallyApi.cancelSubscription(userId);
      if (!isCurrentSession(generation)) return;
      if (userIdRef.current) {
        invalidateSubscription(userIdRef.current);
        invalidateUsage(userIdRef.current);
      }
      setData((current) => current ? { ...current, overview: { ...current.overview, subscription: response.subscription } } : null);
      setNotice(null);
      setSheet({ kind: "cancel-complete" });
      try { await loadData(); }
      catch (caught) { if (isCurrentSession(generation)) handleError(caught); }
    } catch (caught) { if (isCurrentSession(generation)) handleError(caught, true); }
    finally { if (isCurrentSession(generation)) { locked.current = false; setBusy(false); } }
  };

  const statusBadge = subscription?.will_renew
    ? { label: subscription.status === "trialing" ? "무료체험 중" : "이용 중", className: "bg-p-success-container text-p-success" }
    : { label: "자동갱신 꺼짐", className: "bg-p-warning-container text-p-warning" };

  return (
    <AppFrame>
      <TopBar backHref={routes.my} title="요금제 및 결제" variant="back" />
      <div className="flex flex-1 flex-col gap-p-6 px-p-5 pb-p-4 pt-p-2">
        {loading ? (
          <p aria-busy="true" className="flex items-center justify-center gap-p-2 py-p-16 text-p-label text-p-text-secondary" role="status">
            <IconSpinner className="animate-spin motion-reduce:animate-none" size={20} />
            결제 정보를 불러오고 있어요
          </p>
        ) : null}
        {error ? (
          <div className="flex flex-col gap-p-2 rounded-p-card bg-p-error-container px-p-4 py-p-3" role="alert">
            <p className="text-p-small text-p-text">{error}</p>
            <Button className="self-start" disabled={busy} loading={busy} loadingLabel="확인 중…" onClick={() => { void refresh(false); }} size="compact" variant="text">
              다시 확인
            </Button>
          </div>
        ) : null}

        {!loading && data && overview && subscription ? (
          <>
            {pending ? (
              <section aria-labelledby="pending-title" className="flex flex-col gap-p-6">
                <div className="flex flex-col gap-p-2 rounded-p-sheet bg-p-info-container p-p-5" role="status">
                  <h1 className="flex items-center gap-p-2 text-p-card tracking-[-0.02em] text-p-text" id="pending-title">
                    <IconSpinner className="animate-spin text-p-info motion-reduce:animate-none" size={20} />
                    결제 확인 중
                  </h1>
                  <p className="text-p-small text-p-text-secondary">
                    {pending.status === "ready" || pending.status === "preparing"
                      ? "진행 중인 결제가 있어요. 열려 있는 카카오페이 결제창을 확인해 주세요. 결제하지 않았다면 대기 시간이 지난 뒤 다시 고를 수 있어요."
                      : pending.status === "uncertain"
                        ? "결제 결과를 확인하지 못했어요. 다시 결제하지 말고 상태를 다시 확인해 주세요. 이 상태가 계속되면 운영팀의 확인이 필요해요."
                        : "결제 결과를 확인하고 있어요. 다시 결제하지 말고 잠시 뒤 '상태 새로고침'을 눌러 주세요."}
                  </p>
                </div>
                <dl className="flex flex-col gap-p-3 rounded-[20px] bg-p-surface p-p-5">
                  <FactRow label="요금제">{planName(pending.product_id)}</FactRow>
                  <FactRow label="결제 금액">{formatWon(pending.amount)}</FactRow>
                  <FactRow label="현재 이용 상태">{entitled ? "Pally Pro" : "무료"}</FactRow>
                  {entitled && subscription.current_period_end ? <FactRow label="이용 가능일">{formatBillingDate(subscription.current_period_end)}까지</FactRow> : null}
                </dl>
                <Button fullWidth loading={busy} loadingLabel="확인 중…" onClick={() => { void refresh(); }} variant="secondary">
                  상태 새로고침
                </Button>
              </section>
            ) : entitled ? (
              <section aria-labelledby="subscription-title" className="flex flex-col gap-p-6">
                <div className="flex flex-col gap-[14px] rounded-p-sheet bg-p-surface p-p-5">
                  <div className="flex items-center gap-[10px]">
                    <span aria-hidden="true" className="grid size-[36px] shrink-0 place-items-center rounded-[18px] bg-p-secondary-container text-p-secondary">
                      <IconSparkles size={18} />
                    </span>
                    <h1 className="min-w-0 flex-1 font-p-brand text-p-title-en-sm text-p-text" id="subscription-title" lang="en" style={WORDMARK_STYLE}>
                      Pally Pro
                    </h1>
                    <span className={cn("rounded-p-full px-[10px] py-p-1 text-p-eyebrow", statusBadge.className)}>{statusBadge.label}</span>
                  </div>
                  <p className="text-p-small text-p-text-secondary">
                    {subscription.will_renew
                      ? "하루 대화 횟수 제한 없이 이야기할 수 있어요."
                      : subscription.current_period_end
                        ? `${formatBillingDate(subscription.current_period_end)}까지 추가 결제 없이 Pro를 쓸 수 있어요.`
                        : "남은 기간 동안 Pro를 그대로 이용하세요."}
                  </p>
                  <hr className="border-0 border-t border-p-border" />
                  <dl className="flex flex-col gap-p-3">
                    <FactRow emphasis label={subscription.will_renew ? (subscription.status === "trialing" ? "첫 결제일" : "다음 결제일") : "이용 종료일"}>
                      {subscription.current_period_end ? formatBillingDate(subscription.current_period_end) : "확인 필요"}
                    </FactRow>
                    <FactRow label="요금제">{planName(subscription.product_id)}</FactRow>
                    {currentProduct ? <FactRow label="구독 금액">{recurringLabel(currentProduct)}</FactRow> : null}
                    <FactRow label="결제 수단">카카오페이</FactRow>
                  </dl>
                </div>
                {!subscription.will_renew ? <p className="text-p-caption text-p-text-muted">이용 기간이 끝나면 원하는 요금제로 다시 구독할 수 있어요.</p> : null}
              </section>
            ) : purchasable ? (
              <section aria-labelledby="plans-title" className="flex flex-col gap-p-6">
                <div className="flex flex-col gap-p-2">
                  <p className="text-p-eyebrow uppercase text-p-secondary" lang="en">Pally Pro</p>
                  <h1 className="text-p-heading tracking-[-0.02em] text-p-text" id="plans-title">Pally와 더 자유롭게</h1>
                  <p className="text-p-small text-p-text-secondary">나에게 맞는 요금제를 선택하고 Pally와의 대화를 이어가세요.</p>
                  <p className="flex items-center gap-p-2 pt-p-1 text-p-label text-p-text">
                    <IconSparkles className="text-p-secondary" size={18} />
                    하루 대화 횟수 제한 없이 이야기해요
                  </p>
                </div>
                <div aria-labelledby="plan-choice" className="flex flex-col gap-p-3" role="radiogroup">
                  <h2 className="text-p-card tracking-[-0.02em] text-p-text" id="plan-choice">요금제 선택</h2>
                  {[...data.products]
                    .sort((a, b) => (a.interval === "month" ? 0 : 1) - (b.interval === "month" ? 0 : 1))
                    .map((product) => (
                      <PlanCard
                        disabled={busy}
                        key={product.id}
                        onSelect={() => { setSelectedId(product.id); setError(null); }}
                        product={product}
                        selected={selectedId === product.id}
                      />
                    ))}
                  {data.products.length === 0 ? <p className="text-p-small text-p-text-secondary" role="status">현재 고를 수 있는 요금제가 없어요.</p> : null}
                </div>
                <div className="flex items-center gap-[10px] rounded-p-card bg-p-surface px-p-4 py-[14px]">
                  <IconCard className="text-p-text-muted" size={20} />
                  <span className="flex-1 text-p-small text-p-text-muted">결제 수단</span>
                  <span className="text-p-label text-p-text">카카오페이</span>
                </div>
              </section>
            ) : (
              <section aria-labelledby="blocked-title" className="flex flex-col gap-p-4">
                <h1 className="text-p-section tracking-[-0.02em] text-p-text" id="blocked-title">구독 상태 확인</h1>
                <p className="text-p-small text-p-text-secondary">{checkoutBlockMessage(overview)}</p>
                <Button fullWidth loading={busy} loadingLabel="확인 중…" onClick={() => { void refresh(); }} variant="secondary">
                  상태 새로고침
                </Button>
              </section>
            )}

            <section aria-labelledby="history-title" className="flex flex-col gap-p-3">
              <SectionTitle trailing={overview.history_has_more ? <span className="text-p-caption text-p-text-muted">최근 50건</span> : null}>
                <span id="history-title">결제 내역</span>
              </SectionTitle>
              {overview.history.length === 0 ? (
                <p className="text-p-small text-p-text-muted">아직 결제 내역이 없어요.</p>
              ) : (
                <ul className="flex flex-col gap-p-2">
                  {overview.history.map((entry) => (
                    <li key={entry.id}>
                      <button
                        className="flex w-full items-center gap-p-3 rounded-p-card bg-p-surface py-[14px] pl-p-4 pr-p-3 text-left hover:bg-p-raised"
                        onClick={() => { setSheetError(null); setSheet({ kind: "history", entry }); }}
                        type="button"
                      >
                        <IconReceipt className="shrink-0 text-p-text-muted" size={20} />
                        <span className="flex min-w-0 flex-1 flex-col gap-[2px]">
                          <span className="text-p-label text-p-text">{formatBillingDate(entry.approved_at)}</span>
                          <span className="text-p-caption text-p-text-muted">
                            {formatWon(entry.amount)} · {entry.amount === 0 ? "청구 없음" : "결제 완료"} · {planName(entry.product_id)}
                          </span>
                        </span>
                        <IconChevronRight className="shrink-0 text-p-text-muted" size={20} />
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            {entitled && subscription.will_renew ? (
              <div className="flex flex-col gap-p-2">
                <Button disabled={busy || Boolean(pending)} fullWidth onClick={() => { setSheetError(null); setSheet({ kind: "cancel" }); }} variant="secondary">
                  자동갱신 해지
                </Button>
                <p className="text-center text-p-caption text-p-text-muted">요금제를 바꾸려면 자동갱신을 해지하고, 이용 기간이 끝난 뒤 다시 골라 주세요.</p>
              </div>
            ) : null}
          </>
        ) : null}
      </div>

      {!loading && data && purchasable && !pending ? (
        <div className="sticky bottom-0 flex flex-col gap-p-3 bg-p-bg px-p-5 pb-[calc(var(--p-space-6)+env(safe-area-inset-bottom))] pt-p-4">
          {selected ? <p className="text-p-caption text-p-text-muted">{renewalDisclosure(selected)}</p> : null}
          <Button disabled={!selected || busy} fullWidth loading={busy && sheet === null} loadingLabel="확인 중…" onClick={() => { void openCheckout(); }}>
            계속하기
          </Button>
        </div>
      ) : null}

      {notice ? <Toast className="top-[64px]" message={notice} onDismiss={() => setNotice(null)} tone="info" /> : null}

      <Sheet
        actions={
          selected ? (
            <>
              <Button disabled={busy || !purchasable || Boolean(sheetError)} fullWidth loading={busy} loadingLabel="결제 준비 중…" onClick={() => { void startCheckout(); }}>
                {selected.trial_days > 0 ? "카카오페이로 무료체험 시작" : "카카오페이로 결제하기"}
              </Button>
              <Button disabled={busy} fullWidth onClick={closeSheet} variant="text">
                돌아가기
              </Button>
            </>
          ) : null
        }
        description={selected ? `Pally Pro · ${planName(selected.id)}` : undefined}
        onDismiss={busy ? undefined : closeSheet}
        open={sheet?.kind === "checkout" && Boolean(selected)}
        title="구독 시작하기"
      >
        {selected ? (
          <>
            <dl className="flex flex-col gap-p-3 rounded-p-card bg-p-surface p-p-4">
              <FactRow emphasis label="오늘 결제할 금액">{formatWon(firstCharge(selected))}</FactRow>
              <hr className="border-0 border-t border-p-border" />
              <FactRow label="결제 수단">카카오페이</FactRow>
              <FactRow label="정기 결제">{recurringLabel(selected)}</FactRow>
              {selected.trial_days > 0 ? <FactRow label="첫 결제">체험 시작 {selected.trial_days}일 후</FactRow> : null}
            </dl>
            <p className="text-p-caption text-p-text-muted">{renewalDisclosure(selected)}</p>
            {sheetError ? (
              <p className="text-p-small text-p-error" role="alert">
                {sheetError} 창을 닫고 다시 시도해 주세요.
              </p>
            ) : null}
          </>
        ) : null}
      </Sheet>

      <Sheet
        actions={
          <>
            <Button fullWidth loading={busy} loadingLabel="해지 중…" onClick={() => { void stopRenewal(); }}>
              자동갱신 해지하기
            </Button>
            <Button disabled={busy} fullWidth onClick={closeSheet} variant="text">
              계속 이용하기
            </Button>
          </>
        }
        description={`다음 자동 결제만 멈춰요. ${subscription?.current_period_end ? `${formatBillingDate(subscription.current_period_end)}까지 Pro를 그대로 쓸 수 있어요.` : "현재 이용 기간은 그대로 유지돼요."} 이용 기간이 끝나면 원하는 요금제로 다시 구독할 수 있어요.`}
        onDismiss={busy ? undefined : closeSheet}
        open={sheet?.kind === "cancel"}
        title="자동갱신을 해지할까요?"
      >
        {sheetError ? <p className="text-p-small text-p-error" role="alert">{sheetError}</p> : null}
      </Sheet>

      <Sheet
        actions={<Button fullWidth onClick={closeSheet}>확인</Button>}
        description="남은 이용 기간은 그대로 유지돼요."
        onDismiss={closeSheet}
        open={sheet?.kind === "cancel-complete"}
        title="자동갱신을 해지했어요"
      />

      <Sheet
        actions={<Button fullWidth onClick={closeSheet}>확인</Button>}
        description={sheet?.kind === "history" ? `${historyLabel(sheet.entry)} · ${planName(sheet.entry.product_id)}` : undefined}
        onDismiss={closeSheet}
        open={sheet?.kind === "history"}
        title="결제 상세"
      >
        {sheet?.kind === "history" ? (
          <dl className="flex flex-col gap-p-3 rounded-p-card bg-p-surface p-p-4">
            <FactRow emphasis label="결제 금액">{formatWon(sheet.entry.amount)}</FactRow>
            <FactRow label="결제일">{formatBillingDate(sheet.entry.approved_at)}</FactRow>
            <FactRow label="결제 수단">카카오페이</FactRow>
            <FactRow label="상태">{sheet.entry.amount === 0 ? "청구 없음" : "결제 완료"}</FactRow>
          </dl>
        ) : null}
      </Sheet>
    </AppFrame>
  );
}
