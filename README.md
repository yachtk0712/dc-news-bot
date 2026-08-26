# DCNI 데이터센터 산업 뉴스 자동 발송 봇

매일 자동으로 해외(미국 중심) 데이터센터 산업 뉴스를 모아 이메일로 보내드립니다.
Claude나 다른 AI API를 전혀 호출하지 않아 토큰 비용이 들지 않습니다 (RSS + 키워드 필터링만 사용).

## 1. GitHub 저장소 만들기

1. github.com에서 새 저장소(Repository)를 만듭니다. (Private로 만들어도 됩니다)
2. 이 폴더(`dc-news-bot`) 안의 모든 파일을 그 저장소에 업로드합니다.
   - GitHub 웹사이트에서 "Add file → Upload files"로 드래그해서 올려도 되고,
   - `git` 명령어를 아는 경우 아래처럼 해도 됩니다:
     ```
     cd dc-news-bot
     git init
     git add .
     git commit -m "init"
     git remote add origin <내 저장소 주소>
     git push -u origin main
     ```

## 2. Gmail 앱 비밀번호 만들기 (발신용 이메일 계정)

일반 Gmail 로그인 비밀번호는 사용할 수 없고, "앱 비밀번호"라는 별도 비밀번호가 필요합니다.

1. Google 계정 → 보안(Security) → 2단계 인증을 먼저 켭니다 (필수).
2. https://myaccount.google.com/apppasswords 접속
3. 앱 이름을 아무거나 입력(예: "datacenter-news") 하고 생성
4. 나오는 16자리 비밀번호를 복사해둡니다 (이게 SMTP_PASSWORD 입니다)

Gmail이 아닌 다른 메일(네이버, 아웃룩 등)을 쓰고 싶으면 각 서비스의 SMTP 주소/포트를 검색해서 아래 표만 바꾸면 됩니다.

## 3. GitHub 저장소에 비밀값(Secrets) 등록하기

저장소 페이지에서 **Settings → Secrets and variables → Actions → New repository secret** 으로 아래 5개를 하나씩 등록합니다.

| Secret 이름     | 값 예시                    |
|----------------|----------------------------|
| SMTP_HOST      | smtp.gmail.com              |
| SMTP_PORT      | 587                         |
| SMTP_USER      | your@gmail.com              |
| SMTP_PASSWORD  | (2번에서 만든 16자리 앱 비밀번호) |
| MAIL_TO        | 받고 싶은 이메일 주소 (여러 개면 콤마로 구분) |

## 4. 자동 실행 확인

- 위 설정을 마치면 매일 한국시간 오전 7시에 자동으로 실행됩니다.
- 저장소의 **Actions** 탭 → **Daily Data Center News** → **Run workflow** 버튼으로 지금 바로 한 번 테스트해볼 수 있습니다.
- 실행 시간을 바꾸고 싶으면 `.github/workflows/daily-datacenter-news.yml` 파일의 `cron` 값을 수정하세요.
  (cron은 UTC 기준입니다. 한국시간 = UTC + 9시간)

## 5. 뉴스 소스/키워드 커스터마이징

`fetch_datacenter_news.py` 파일 상단의 두 부분만 수정하면 됩니다.

- `RSS_FEEDS`: 추적하고 싶은 뉴스 사이트의 RSS 주소를 추가/삭제
- `KEYWORDS`: 어떤 단어가 포함된 기사만 뽑을지 (지금은 데이터센터/전력망/AI 인프라 중심)

## 문제가 생기면

- Actions 탭에서 실행 로그를 확인하면 어느 단계에서 실패했는지 나옵니다.
- 가장 흔한 실패 원인은 Secrets 오타이거나 Gmail 앱 비밀번호를 잘못 넣은 경우입니다.
