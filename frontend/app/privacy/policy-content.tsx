import type { ReactNode } from "react";

// Keep this in step with what the app actually stores and where it sends it.
// Sources: supabase/migrations (tables, cascades), backend/main.py (Google calls,
// in-memory audio), ai/tracing.py (Langfuse), frontend/app/page.tsx (OAuth scopes).
export const POLICY_EFFECTIVE_DATE = "2026년 11월 26일";

const PRIVACY_CONTACT = { owner: "Puter", email: "pally.pally2026@gmail.com" } as const;

type PolicySection = { title: string; body: ReactNode };

function Items({ items }: { items: ReadonlyArray<ReactNode> }) {
  return (
    <ul className="flex list-disc flex-col gap-p-1 pl-p-5">
      {items.map((item, index) => <li key={index}>{item}</li>)}
    </ul>
  );
}

export const POLICY_SECTIONS: ReadonlyArray<PolicySection> = [
  {
    title: "1. 처리하는 개인정보 항목",
    body: (
      <Items
        items={[
          "로그인 정보: Google 로그인 시 이메일·이름·프로필 사진, 카카오 로그인 시 닉네임·프로필 사진 (카카오 이메일은 받지 않아요)",
          "프로필: 표시 이름, 영어 레벨, 온보딩 완료 여부",
          "대화 기록: 내 말을 받아 적은 글, Pally의 답변, 교정 피드백, 대화 제목과 시간",
          "말투 분석 결과: 대화별 5가지 말투 점수와 Pally의 현재 모습",
          "목소리 기준값: 온보딩에서 등록한 억양 측정값 (녹음 원본은 저장하지 않아요)",
          "대화에서 기억한 정보: 대화 중 직접 말한 이름·나이·사는 곳·직업·학교·전공·가족·반려동물·취미·계획 같은 사실",
          "이용 기록: 일일 사용량, 연속 학습일, 업적, 오늘의 표현·과제 기록, 화면 이용 이벤트",
          "결제 정보(테스트): 구독 상태, 주문 번호와 결제 상태. 카드 번호 등 결제 수단 정보는 카카오페이가 처리하고 Puter는 받지 않아요",
        ]}
      />
    ),
  },
  {
    title: "2. 처리 목적",
    body: (
      <Items
        items={[
          "회원 식별과 로그인 유지",
          "영어 대화 진행: 음성을 글로 바꾸고, Pally의 답변과 목소리를 만들고, 표현을 교정해 드리기 위해",
          "내 말투를 닮아 가는 Pally의 모습과 말투를 만들기 위해",
          "이전 대화에서 말한 내용을 기억해 다음 대화를 자연스럽게 이어 가기 위해",
          "사용량 관리, 학습 기록·업적 제공, 서비스 오류 확인과 개선",
          "구독 결제 처리(현재는 카카오페이 테스트 결제만 운영해요)",
        ]}
      />
    ),
  },
  {
    title: "3. 보유 기간과 파기",
    body: (
      <>
        <Items
          items={[
            "모든 개인정보는 회원탈퇴 시 지체 없이 삭제해요. 탈퇴하면 대화 기록, 목소리 기준값, 기억한 정보, 이용·결제 기록이 한 번에 지워져요.",
            "마이 페이지의 ‘대화 기록 삭제’로 언제든 대화 기록을 지울 수 있어요. 이때 그 대화에서 기억한 정보도 함께 지워지고 Pally는 처음 모습으로 돌아가요.",
            "대화 중 녹음한 음성은 글로 바꾸는 데에만 쓰고 저장하지 않아요. 온보딩 녹음도 억양을 측정한 뒤 바로 버려요.",
            "AI 답변 오류를 확인하려고 남기는 기록(Langfuse)은 회원탈퇴나 대화 기록 삭제와 별개로, 기록한 날부터 30일이 지나면 자동으로 삭제돼요.",
          ]}
        />
        <p>전자적 파일은 복구할 수 없는 방법으로 데이터베이스에서 삭제해요.</p>
      </>
    ),
  },
  {
    title: "4. 제3자 제공",
    body: <p>Puter는 이용자의 개인정보를 제3자에게 제공하지 않아요. 법령에 특별한 규정이 있는 경우만 예외예요.</p>,
  },
  {
    title: "5. 처리 위탁과 국외 이전",
    body: (
      <>
        <p>서비스 운영을 위해 아래 업체에 개인정보 처리를 맡기고 있어요. 일부 업체는 서버가 해외에 있어 개인정보가 국외로 전송돼요. 전송은 서비스를 이용할 때마다 암호화된 통신(HTTPS)으로 이뤄져요.</p>
        <Items
          items={[
            "Supabase (데이터베이스·로그인) — 서울 리전에 저장",
            "Google LLC, 미국 (Speech-to-Text·Text-to-Speech·Gemini API) — 대화 음성과 글을 보내 글 변환, 답변·목소리 생성, 교정, 말투 분석에 사용",
            "Railway, 싱가포르 리전 (백엔드 서버) — 요청을 처리하는 동안 대화 음성과 글을 다룸",
            "Vercel Inc., 미국 (웹 화면 배포) — 화면 파일 전송, 접속 기록",
            "ClickHouse, Inc. (Langfuse), 미국 (AI 답변 기록) — Gemini에 보낸 대화 글·기억한 정보와 Pally의 답변을 오류 확인과 품질 개선에 사용, 30일 보관",
            "Google·카카오 (소셜 로그인), 카카오페이 (테스트 결제)",
          ]}
        />
        <p>국외 이전을 원하지 않으면 회원탈퇴로 언제든 거부할 수 있어요. 다만 이 업체들 없이는 대화 기능을 제공할 수 없어요.</p>
      </>
    ),
  },
  {
    title: "6. 이용자의 권리와 행사 방법",
    body: (
      <>
        <p>이용자는 언제든 자신의 개인정보를 열람·정정·삭제하거나 처리 정지를 요구할 수 있어요.</p>
        <Items
          items={[
            "열람: 피드백 탭과 마이 페이지에서 대화 기록과 프로필을 바로 볼 수 있어요",
            "정정: 마이 페이지에서 이름과 영어 레벨을 바꿀 수 있어요",
            "삭제: 마이 페이지의 ‘대화 기록 삭제’와 ‘회원탈퇴’",
            "그 밖의 요청은 아래 연락처로 보내 주시면 지체 없이 처리할게요",
          ]}
        />
      </>
    ),
  },
  {
    title: "7. 안전성 확보 조치",
    body: (
      <Items
        items={[
          "모든 통신은 HTTPS로 암호화해요",
          "데이터베이스의 모든 표에 행 단위 보안(RLS)을 켜서, 로그인한 본인의 기록만 읽을 수 있게 했어요",
          "서버는 로그인 토큰으로 사용자를 확인하고, 요청에 적힌 사용자 번호는 믿지 않아요",
          "서버 키와 API 키는 코드에 넣지 않고 서버 환경 변수로만 관리해요",
          "대화 처리 기록(로그)에는 대화 내용 대신 글자 수와 처리 시간만 남겨요",
        ]}
      />
    ),
  },
  {
    title: "8. 자동 수집 장치",
    body: (
      <p>
        로그인 상태 유지를 위해 브라우저 저장소에 로그인 세션을, 이어 하던 대화로 돌아가기 위해 대화 번호를 저장해요.
        광고나 추적용 쿠키는 쓰지 않아요. 브라우저 설정에서 사이트 데이터를 지우면 로그아웃돼요.
      </p>
    ),
  },
  {
    title: "9. 이용 연령",
    body: (
      <p>
        Pally는 만 12세 이상을 대상으로 해요. 만 12세 미만 아동의 개인정보는 알면서 수집하지 않아요. 만 14세 미만
        이용자는 「개인정보 보호법」에 따라 법정대리인(보호자)의 동의를 받은 뒤 이용해야 해요.
      </p>
    ),
  },
  {
    title: "10. 개인정보 보호책임자",
    body: (
      <>
        <p>개인정보와 관련한 문의, 불만, 피해 구제는 아래로 연락해 주세요.</p>
        <Items
          items={[
            `책임자: ${PRIVACY_CONTACT.owner}`,
            <a className="underline" href={`mailto:${PRIVACY_CONTACT.email}`} key="mail">{PRIVACY_CONTACT.email}</a>,
          ]}
        />
        <p>개인정보 침해에 대한 신고나 상담은 개인정보침해신고센터(국번 없이 118), 개인정보분쟁조정위원회(1833-6972)에도 할 수 있어요.</p>
      </>
    ),
  },
  {
    title: "11. 방침 변경",
    body: <p>이 방침이 바뀌면 시행 7일 전부터 이 화면에 알려 드려요.</p>,
  },
];
