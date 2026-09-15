import streamlit as st
from google import genai
import urllib.parse
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

st.set_page_config(
    page_title="YoungMom Canada 블로그 비서", 
    page_icon="🍁", 
    layout="centered"
)

st.title("🍁 YoungMom Canada 글 생성기")
st.caption("대표 사진과 본문 사진 2장이 적재적소에 들어간 실전 포스팅을 블로그에 바로 등록합니다.")

# 1. 환경 변수(Secrets) 연동
api_key = st.secrets.get("GEMINI_API_KEY")
sender_email = st.secrets.get("SENDER_EMAIL")
app_password = st.secrets.get("GMAIL_APP_PASSWORD")
blogger_email = st.secrets.get("BLOGGER_EMAIL")

# 로컬 테스트용 사이드바 (배포 환경에서 Secrets가 없을 때 대비)
if not all([api_key, sender_email, app_password, blogger_email]):
    with st.sidebar:
        st.header("⚙️ 환경 설정 (Secrets 미설정 시)")
        api_key = api_key or st.text_input("Gemini API Key", type="password")
        sender_email = sender_email or st.text_input("발송용 Gmail 주소")
        app_password = app_password or st.text_input("Gmail 앱 비밀번호(16자리)", type="password")
        blogger_email = blogger_email or st.text_input("블로그스팟 비밀 이메일")

if not all([api_key, sender_email, app_password, blogger_email]):
    st.info("💡 설정값(API 키 및 이메일 계정)이 준비되면 글 생성을 시작할 수 있습니다.")
    st.stop()

# 2. 어머님 맞춤형 입력 UI
category = st.selectbox(
    "1. 카테고리 선택",
    [
        "🏠 렌트 & 이사 (디파짓 반환, 계약서 확인, 인스펙션)",
        "📑 알버타 행정 & 서류 (운전면허 교환, 헬스케어 카드, 유심)",
        "🚗 겨울철 차량 & 생활 안전 (스노우 타이어, 블록히터, 한파 대비)",
        "🛒 현지 알뜰 장보기 (코스트코, 수퍼스토어 꿀템/가격 비교)",
        "✏️ 기타 직접 입력"
    ]
)

topic = st.text_input(
    "2. 핵심 주제", 
    placeholder="예: 무빙아웃 인스펙션 집주인 보증금 공제 분쟁"
)

experience = st.text_area(
    "3. 💡 실제 겪으신 일이나 기억나는 상황 (한 줄만 적어주세요)", 
    placeholder="예: 이사 나갈 때 벽에 못 자국 2개 있다고 $150 깎겠다고 해서 당황했음\n(비워두셔도 자연스러운 예시로 글이 완성됩니다)",
    height=85
)

# 3. 자동 생성 및 전송 로직
if st.button("🚀 블로그에 글 & 사진 2장 바로 등록하기", type="primary", use_container_width=True):
    if not topic:
        st.warning("주제를 입력해 주세요.")
    else:
        with st.spinner("경험담을 반영해 사진 2장과 실전 포스팅을 완성하여 블로그로 전송 중입니다..."):
            try:
                # 경험담 입력 여부에 따른 프롬프트 분기
                if experience.strip():
                    exp_rule = f"""
                    - [필수 반영 경험담]: "{experience.strip()}"
                    - 지침: 위 경험을 글 도입부에 생생한 계기("저희도 이번에 이사하면서 ~한 일을 겪었거든요")로 자연스럽게 풀어내고, 본문 해결 팁 중 하나에서 이 사례를 어떻게 해결했는지 직접 다루세요.
                    """
                else:
                    exp_rule = """
                    - 지침: 알버타 교민들이 렌트나 현지 생활 중 흔히 겪는 가장 현실적인 당황스러운 상황 1가지를 자연스러운 경험담처럼 서두에 배치하세요.
                    """

                prompt = f"""
                당신은 캐나다 알버타에서 생활하는 인기 블로그(Youngmom-canada-life) 운영자입니다.
                구글 블로그스팟에 등록할 실전 정보 글을 작성하세요.

                [카테고리]: {category}
                [주제]: {topic}
                {exp_rule}

                [필수 작성 규칙]
                1. 첫 줄은 반드시 "TITLE: [한글 블로그 제목]" 형식으로 작성하세요.
                2. 말투: 다정하면서도 명쾌한 선배 맘 안내형 구어체 (~하는 것이 안전합니다, ~확인해 보세요).
                3. 검색 찌꺼기 텍스트(A, Alberta.ca, +1 등) 절대 금지.
                4. 본문 구성:
                   - 도입부: 실제 겪은 상황 공유 및 공감 질문
                   - 본문 팁 1번
                   - 본문 팁 2번 바로 직전 줄에 정확히 "[INSERT_BODY_IMAGE]" 태그를 한 줄로 삽입하세요.
                   - 본문 팁 2번, 3번 (현지 대응 수칙)
                   - 실전 템플릿: 집주인이나 관공서에 바로 복사해 보낼 수 있는 간단한 영어 문자/이메일 박스
                   - 요약: [한눈에 보는 순서 요약] (화살표 ↓ 활용)
                   - 따뜻한 마무리 맺음말
                5. 글 맨 마지막에 아래 2줄을 정확히 작성하세요:
                   THUMBNAIL_PROMPT: [글 전체를 상징하는 따뜻한 캐나다 일상 실사 사진 영문 묘사]
                   BODY_PROMPT: [본문 팁과 관련된 서류, 노트북, 체크리스트 등 디테일한 오브젝트 사진 영문 묘사]
                """

                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=prompt
                )
                full_text = response.text

                # 제목 추출
                post_title = "캐나다 알버타 실전 생활 꿀팁"
                if "TITLE:" in full_text:
                    parts = full_text.split("TITLE:", 1)[1].split("\n", 1)
                    post_title = parts[0].strip()
                    full_text = parts[1] if len(parts) > 1 else ""

                # 이미지 프롬프트 추출
                thumb_prompt = f"Cozy realistic photo about {topic} in Alberta Canada, warm aesthetic"
                body_prompt = f"Close up photo of documents, checklist, or home details related to {topic}, bright lighting"

                if "THUMBNAIL_PROMPT:" in full_text and "BODY_PROMPT:" in full_text:
                    main_body, prompts_part = full_text.rsplit("THUMBNAIL_PROMPT:", 1)
                    thumb_part, body_part = prompts_part.split("BODY_PROMPT:", 1)
                    thumb_prompt = thumb_part.strip()
                    body_prompt = body_part.strip()
                else:
                    main_body = full_text

                # 이미지 URL 생성 (무료 고화질 엔드포인트)
                thumb_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(thumb_prompt)}?width=900&height=550&nologo=true"
                body_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(body_prompt)}?width=900&height=500&nologo=true"

                # 본문 중간 이미지 태그 치환
                body_img_html = f"""
                <div style="text-align: center; margin: 30px 0;">
                    <img src="{body_url}" style="width: 100%; max-width: 750px; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.08);" alt="관련 팁 사진" />
                </div>
                """

                if "[INSERT_BODY_IMAGE]" in main_body:
                    html_body_text = main_body.replace("[INSERT_BODY_IMAGE]", body_img_html)
                else:
                    html_body_text = main_body + body_img_html

                # 줄바꿈 및 전체 HTML 패키징 (상단 썸네일 + 본문 + 중간 이미지)
                formatted_body = html_body_text.strip().replace("\n", "<br>")
                final_html = f"""
                <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.85; font-size: 16px; color: #333;">
                    <div style="text-align: center; margin-bottom: 25px;">
                        <img src="{thumb_url}" style="width: 100%; max-width: 800px; border-radius: 10px;" alt="대표 사진" />
                    </div>
                    {formatted_body}
                </div>
                """

                # 이메일 전송 (Blogger Mail2Blogger)
                msg = MIMEMultipart()
                msg['Subject'] = post_title
                msg['From'] = sender_email
                msg['To'] = blogger_email
                msg.attach(MIMEText(final_html, 'html', 'utf-8'))

                with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                    server.login(sender_email, app_password)
                    server.send_message(msg)

                st.success(f"🎉 전송 완료! 블로그에 '{post_title}' 글이 성공적으로 등록되었습니다.")

                # 화면 미리보기
                st.markdown("### 🖼️ 첨부된 이미지 2장 미리보기")
                col1, col2 = st.columns(2)
                with col1:
                    st.caption("1. 상단 대표 사진 (썸네일)")
                    st.image(thumb_url, use_container_width=True)
                with col2:
                    st.caption("2. 본문 중간 사진 (시선 환기용)")
                    st.image(body_url, use_container_width=True)

                st.markdown("### 📝 전송된 포스팅 내용")
                st.markdown(main_body.replace("[INSERT_BODY_IMAGE]", "\n\n*(여기에 2번째 사진이 자동 배치되었습니다)*\n\n"))

            except Exception as e:
                st.error(f"등록 중 오류가 발생했습니다: {e}")
