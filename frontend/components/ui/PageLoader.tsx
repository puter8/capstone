type PageLoaderProps = {
  message?: string;
};

export function PageLoader({ message = "불러오는 중이에요" }: PageLoaderProps) {
  return (
    <div aria-live="polite" className="absolute inset-0 z-[100] flex flex-col items-center justify-center gap-5 bg-surface" role="status">
      <span aria-hidden="true" className="size-14 animate-spin rounded-full border-4 border-primary-soft border-t-primary" />
      <p className="text-body text-primary">{message}</p>
    </div>
  );
}
