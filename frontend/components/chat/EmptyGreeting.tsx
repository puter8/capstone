export function EmptyGreeting() {
  return (
    <div className="flex flex-col items-center gap-4 text-center px-9">
      <p className="text-text font-sans font-semibold text-[18px] leading-6">
        오늘은 어떤 이야기를 해볼까요?
      </p>
      <p className="text-text-tertiary font-sans text-[14px] leading-5">
        마이크를 눌러 영어로 말해보세요
      </p>
    </div>
  );
}
