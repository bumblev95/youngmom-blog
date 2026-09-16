import streamlit as st
from google import genai
import urllib.parse
import urllib.request
import smtplib
import random
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

st.set_page_config(page_title="영맘 캐나다 라이프 블로그 비서", page_icon="🍁", layout="centered")

st.title("🍁 영맘 캐나다 라이프 글 생성기")
st.caption("깨짐 없는 초고화질 실사 사진과 함께 글을 완성하고 블로그에 등록하세요.")

# 1. 환경 변수(Secrets) 연동
api_key = st.secrets.get("GEMINI_API_KEY")
sender_email = st.secrets.get("SENDER_EMAIL")
app_password = st.secrets.get("GMAIL_APP_PASSWORD")
blogger_email = st.secrets.get("BLOGGER_EMAIL")

if not all([api_key, sender_email, app_password, blogger_email]):
    st.error("Streamlit Secrets에 필수 설정(API 키, 이메일 정보)이 누락되었습니다.")
    st.stop()

# 2. 세션 상태 초기화
if "post_data" not in st.session_state:
    st.session_state.post_data = None

# 초고화질 실사 정물 사진 URL 생성 함수 (flux-realism + 1200px 와이드)
def generate_hd_image_url(prompt_text, width, height, seed):
    # 인물 얼굴 깨짐을 원천 차단하고 사물/공간의 선명도를 극대화하는 옵션
    camera_style = ", professional editorial still-life photography, shot on Hasselblad 50mm lens, ultra sharp focus, crisp details, natural soft daylight, clean aesthetic, 8k resolution, photorealistic, no people, no distorted faces, no human, no blur, no text, no watermark"
    enhanced_prompt = prompt_text + camera_style
    encoded = urllib.parse.quote(enhanced_prompt)
    return f"https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}&model=flux-realism&nologo=true&seed={seed}"

# --- [1단계: 입력 섹션] ---
st.markdown("### 📝 1단계: 글 재료 입력하기")

category = st.selectbox(
    "1. 카테고리 선택",
    [
        "🏠 렌트 & 이사 (디파짓 반환, 계약서, 인스펙션)",
        "📑 알버타 행정 & 서류 (운전면허, 헬스케어, 연금, 혜택)",
        "🚗 겨울철 차량 & 생활 안전 (타이어, 한파 대비, 대출 주의)",
        "🛒 현지 알뜰 장보기 (코스트코, 마트 꿀템/물가 비교)",
        "✏️ 기타 캐나다 일상"
    ]
)

topic = st.text_input(
    "2. 핵심 주제", 
    placeholder="예: 캐나다 연금(CPP/OAS) 신청 자격과 받는 시기"
)

source_content = st.text_area(
    "3. 📰 참고할 기사나 다른 글 내용 (선택: 복사해서 붙여넣기)",
    placeholder="뉴스 기사, 정부 공지문, 카페 글 등 참고하고 싶은 원문을 통째로 붙여넣으세요.\n(AI가 핵심 사실만 뽑아 완전히 새로운 엄마만의 글로 다시 씁니다)",
    height=120
)

experience = st.text_area(
    "4. 💡 엄마의 실제 경험이나 생각 (선택: 한 줄만 편하게)", 
    placeholder="예: 주변 지인이 은퇴 나이 다 됐는데 신청 늦게 해서 손해 봤다고 들었음\n(비워두셔도 자연스럽게 완성됩니다)",
    height=80
)

if st.button("🔍 고화질 사진 & 초안 만들기 (미리보기)", type="primary", use_container_width=True):
    if not topic.strip():
        st.warning("핵심 주제를 입력해 주세요.")
    else:
        with st.spinner("깨짐 없는 선명한 화보 사진 2장과 글 초안을 생성하는 중입니다..."):
            try:
                source_instruction = ""
                if source_content.strip():
                    source_instruction = f"""
                    [참고할 원문 데이터]:
                    \"\"\"{source_content.strip()}\"\"\"
                    - 핵심 지침: 원문의 문장을 베끼지 말고 핵심 팩트와 숫자만 추출하여 엄마만의 생생한 말투로 재창작하세요.
                    """

                exp_instruction = ""
                if experience.strip():
                    exp_instruction = f"""
                    - [엄마의 실제 경험/생각]: "{experience.strip()}"
                    - 지침: 위 경험을 글 도입부의 생생한 계기나 본문 팁에 자연스럽게 녹여내세요.
                    """
                else:
                    exp_instruction = "- 지침: 알버타 교민들이 흔히 겪는 고민이나 궁금증을 서두에 배치해 공감을 얻으세요."

                prompt = f"""
                당신은 캐나다 알버타에서 유용한 생활 꿀팁을 전하는 블로거 '영맘 캐나다 라이프'입니다.
                블로그스팟에 발행할 실용적이고 읽기 편한 포스팅을 작성하세요.

                [카테고리]: {category}
                [주제]: {topic}
                {source_instruction}
                {exp_instruction}

                [필수 작성 규칙]
                1. 첫 줄은 반드시 "TITLE: [한글 블로그 제목]" 형식이어야 합니다.
                2. 블로그 이름이나 인사말에 영문(Youngmom-canada-life)을 절대 쓰지 마세요.
                   반드시 자연스러운 한글로 "영맘 캐나다 라이프"라고 소개하세요.
                   (예시: "안녕하세요, 알버타 이웃 여러분! 영맘 캐나다 라이프입니다 🍁")
                3. 구성:
                   - 도입부: 다정한 첫인사 및 주제 선정 계기/공감 질문
                   - 본문 팁 1번, 2번, 3번 (현실적인 팁과 주의사항, 상세 해결책)
                   - 실전 템플릿: 관공서/현지에 문의할 때 쓰는 간단한 영어 문장 박스
                   - 요약: [한눈에 보는 핵심 요약] (화살표 ↓ 활용)
                   - 다정한 맺음말
                4. 사진 묘사 규칙 (중요: 인물 얼굴 배제, 선명한 정물/배경 중심):
                   THUMBNAIL_PROMPT: [Editorial still-life photo of a cozy Canadian living space desk related to '{topic}', wooden table, planner, warm coffee mug, soft window sunlight, crisp and sharp]
                   BODY_PROMPT: [Top-down flatlay photo of paperwork, checklist notebook, eyeglasses, and pen on a bright wooden desk related to '{topic}', highly detailed texture]
                """

                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=prompt
                )
                full_text = response.text

                # 제목 분리
                post_title = topic
                if "TITLE:" in full_text:
                    parts = full_text.split("TITLE:", 1)[1].split("\n", 1)
                    post_title = parts[0].strip()
                    full_text = parts[1] if len(parts) > 1 else ""

                # 이미지 프롬프트 분리
                thumb_prompt = f"Editorial still-life photo related to {topic} with warm coffee mug, planner, sunny Canadian window"
                body_prompt = f"Flatlay close-up photo of paperwork checklist notebook and pen on wooden desk regarding {topic}"

                if "THUMBNAIL_PROMPT:" in full_text and "BODY_PROMPT:" in full_text:
                    main_body, prompts_part = full_text.rsplit("THUMBNAIL_PROMPT:", 1)
                    thumb_part, body_part = prompts_part.split("BODY_PROMPT:", 1)
                    thumb_prompt = thumb_part.strip()
                    body_prompt = body_part.strip()
                else:
                    main_body = full_text

                # 1200x675 고해상도 (16:9 와이드) 생성
                thumb_seed = random.randint(1000, 999999)
                body_seed = random.randint(1000, 999999)

                thumb_url = generate_hd_image_url(thumb_prompt, 1200, 675, thumb_seed)
                body_url = generate_hd_image_url(body_prompt, 1200, 675, body_seed)

                st.session_state.post_data = {
                    "title": post_title,
                    "body": main_body.strip(),
                    "thumb_prompt": thumb_prompt,
                    "body_prompt": body_prompt,
                    "thumb_seed": thumb_seed,
                    "body_seed": body_seed,
                    "thumb_url": thumb_url,
                    "body_url": body_url
                }

            except Exception as e:
                st.error(f"초안 생성 중 오류가 발생했습니다: {e}")

# --- [2단계: 검토 및 최종 발행 섹션] ---
if st.session_state.post_data:
    st.divider()
    st.markdown("### 🔍 2단계: 엄마의 검토 및 사진 확인 (Review)")
    st.info("💡 사진과 글을 확인하세요. 사진이 마음에 안 들면 **[🔄 다른 사진 뽑기]**를 누르면 바로 바뀝니다!")

    # 1. 제목 수정
    reviewed_title = st.text_input(
        "블로그 제목 확인/수정", 
        value=st.session_state.post_data["title"]
    )

    # 2. 이미지 미리보기 및 다시 뽑기
    st.markdown("##### 🖼️ 함께 등록될 초고화질 사진 2장")
    col1, col2 = st.columns(2)
    
    with col1:
        st.caption("1. 대표 사진 (썸네일)")
        st.image(st.session_state.post_data["thumb_url"], use_container_width=True)
        if st.button("🔄 대표 사진 다른 걸로 바꾸기", key="regen_thumb"):
            new_seed = random.randint(1000, 999999)
            st.session_state.post_data["thumb_seed"] = new_seed
            st.session_state.post_data["thumb_url"] = generate_hd_image_url(
                st.session_state.post_data["thumb_prompt"], 1200, 675, new_seed
            )
            st.rerun()

    with col2:
        st.caption("2. 본문 사진")
        st.image(st.session_state.post_data["body_url"], use_container_width=True)
        if st.button("🔄 본문 사진 다른 걸로 바꾸기", key="regen_body"):
            new_seed = random.randint(1000, 999999)
            st.session_state.post_data["body_seed"] = new_seed
            st.session_state.post_data["body_url"] = generate_hd_image_url(
                st.session_state.post_data["body_prompt"], 1200, 675, new_seed
            )
            st.rerun()

    # 3. 본문 수정
    reviewed_body = st.text_area(
        "본문 내용 확인/수정", 
        value=st.session_state.post_data["body"],
        height=350
    )

    # 4. 최종 자동 발행 버튼
    col_send, col_cancel = st.columns([3, 1])
    with col_send:
        if st.button("🚀 검토 완료! 블로그에 최종 발행하기", type="primary", use_container_width=True):
            with st.spinner("초고화질 사진을 준비하여 블로그로 전송 중입니다..."):
                try:
                    headers = {'User-Agent': 'Mozilla/5.0'}
                    req1 = urllib.request.Request(st.session_state.post_data["thumb_url"], headers=headers)
                    thumb_bytes = urllib.request.urlopen(req1, timeout=25).read()

                    req2 = urllib.request.Request(st.session_state.post_data["body_url"], headers=headers)
                    body_bytes = urllib.request.urlopen(req2, timeout=25).read()

                    formatted_body = reviewed_body.strip().replace("\n", "<br>")
                    final_html = f"""
                    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.85; font-size: 16px; color: #333;">
                        {formatted_body}
                    </div>
                    """

                    msg = MIMEMultipart()
                    msg['Subject'] = reviewed_title
                    msg['From'] = sender_email
                    msg['To'] = blogger_email
                    msg.attach(MIMEText(final_html, 'html', 'utf-8'))

                    # 고해상도 첨부파일 동봉
                    img1 = MIMEImage(thumb_bytes, name="featured_photo.jpg")
                    img1.add_header('Content-Disposition', 'attachment', filename='featured_photo.jpg')
                    msg.attach(img1)

                    img2 = MIMEImage(body_bytes, name="content_photo.jpg")
                    img2.add_header('Content-Disposition', 'attachment', filename='content_photo.jpg')
                    msg.attach(img2)

                    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                        server.login(sender_email, app_password)
                        server.send_message(msg)

                    st.success(f"🎉 성공적으로 자동 등록되었습니다! '{reviewed_title}'")
                    st.balloons()
                    st.session_state.post_data = None

                except Exception as e:
                    st.error(f"발행 중 오류가 발생했습니다: {e}")

    with col_cancel:
        if st.button("❌ 취소", use_container_width=True):
            st.session_state.post_data = None
            st.rerun()
