from flask import Flask, render_template, request, redirect
from recommender.core import MakeupRecommender
from recommender.core import STYLE_TAG_MAPPER, BROAD_MOOD_MAPPER, CONSTRAINT_MAPPER

app = Flask(__name__)

# CSV 테스트모드
# ====================================
# 엔진 생성
# ====================================
engine = MakeupRecommender(
    use_csv_for_test=True,
    csv_path=r"C:\2025_2\최종_전처리완료_정리3.csv"


)

from openai import OpenAI
import os

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다!")

client = OpenAI(api_key=api_key)

# ==========================================
# 0. Start Page
# ==========================================
@app.route("/start")
def start():
    return render_template("start.html")


# 기본 홈 → start 페이지로 이동
@app.route("/")
def index():
    return redirect("/start")

# STEP1
@app.route("/profile1")
def profile1():
    return render_template("step1_profile.html")


# STEP1 → STEP2 INTRO
@app.route("/profile2", methods=["POST"])
def profile2():
    return render_template(
        "step2_tone_intro.html",
        nickname=request.form["nickname"],
        face_shape=request.form["face_shape"]
    )


# STEP2 QUIZ
@app.route("/tone_quiz", methods=["POST"])
def tone_quiz():
    return render_template(
        "step2_tone_quiz.html",
        nickname=request.form["nickname"],
        face_shape=request.form["face_shape"]
    )

@app.route("/step2_tone", methods=["POST"])
def step2_tone():
    return render_template(
        "step2_tone.html",
        nickname=request.form["nickname"],
        face_shape=request.form["face_shape"]
    )

# STEP3: TPO 선택
@app.route("/occasion", methods=["POST"])
def occasion():
    return render_template(
        "occasion.html",
        nickname=request.form["nickname"],
        face_shape=request.form["face_shape"],
        tone=request.form["tone"]
    )


# ==========================================
# 4. STEP4: Mood / Wannabe 선택
# ==========================================
@app.route("/mood", methods=["POST"])
def mood():
    return render_template(
        "mood.html",
        nickname=request.form["nickname"],
        face_shape=request.form["face_shape"],
        tone=request.form["tone"],
        occasion=request.form["occasion"],
        tags=request.form.get("tags", "")
    )


# ==========================================
# 5. 제약조건 선택 페이지
# ==========================================

# app.py

@app.route("/constraints", methods=["POST"])
def constraints():

    face_shape = request.form.get("face_shape", "")   # ⭐ 절대 누락 방지


    # 1. Form 데이터 받아오기 (기존 코드 유지)
    tone = request.form.get("tone")
    occasion = request.form.get("occasion")
    moods_raw = request.form.get("moods", "")
    moods = moods_raw if moods_raw not in ["", "[]", None] else None
    tab_mode = request.form.get("tab_mode")
    tags = request.form.get("tags")
    style_tag = request.form.get("style_tag")

    # 2. 변수 할당 (지우지 마세요! 그대로 두세요)
    user_occasion = occasion
    user_mood = moods

    # 3. [NEW] 세부 태그를 리스트로 변환하는 로직 추가
    # (tags 문자열을 콤마로 쪼개서 리스트로 만듦)
    tags_raw = request.form.get("tags", "")
    selected_tags_list = [t for t in tags_raw.split(",") if t]

    # 4. 제약조건 받아오기
    # app.py의 /constraints 함수 (수정 코드)

    # 4. 제약조건 받아오기 (프론트에서 문자열로 왔으므로, 문자열로 받고 콤마로 쪼개 리스트로 변환)
    constraints_raw = request.form.get("constraints", "")
    selected_constraints = [t.strip() for t in constraints_raw.split(',') if t.strip()]

    # 5. [수정됨] available_tags 호출 (인자 5개 모두 전달!)
    available_tags = engine.get_available_tags(
        user_occasion_group=user_occasion,    # 대분류도 주고
        user_mood_group=user_mood,            # 대분류도 주고
        style_tag=style_tag,
        user_tone=tone,                       # 톤 정보도 주고
        selected_pre_tags=selected_tags_list  # ⭐ [핵심] 세부 태그 리스트도 줌
    )

    # 6. [수정됨] compatible 호출 (인자 6개 모두 전달!)
    compatible = engine.get_compatible_tags(
        selected_constraints,
        user_occasion_group=occasion,         # 대분류
        user_mood_group=moods,                # 대분류
        style_tag=style_tag,
        user_tone=tone,                       # 톤
        selected_pre_tags=selected_tags_list  # ⭐ [핵심] 세부 태그 리스트
    )

    # compatible = [] 인 경우 → 모든 버튼 disabled
    if compatible == []:
        final_available = []
    else:
        final_available = list((set(available_tags) & set(compatible)) | set(selected_constraints))

    return render_template(
        "constraints.html",
        tone=tone,
        occasion=occasion,
        moods=moods,
        tab_mode=tab_mode,
        tags=tags,
        style_tag=style_tag,
        selected_constraints=selected_constraints,
        available_tags=final_available,
        face_shape=face_shape,
        nickname=request.form.get("nickname", "")
    )

def generate_llm_style_tip(
    user_face_shape,
    user_tone,
    user_tpo,
    user_mood,
    video_title,
    video_keywords
):
    system_instruction = """
당신은 청담동에서 10년 이상 활동한 ‘퍼스널 메이크업 전문 컨설턴트’입니다.
당신의 임무는 사용자의 [얼굴형, 퍼스널컬러, 상황, 분위기] 정보를 바탕으로,
추천된 메이크업 영상의 기법을 ‘사용자에게 맞게 변형’하여 실전 조언을 해주는 것입니다.

[말하기 규칙]
1. 20대 여성 친구에게 말하듯 다정하고 신뢰감 있는 말투(“~해요”, “~네요”)를 사용하세요.
2. 영상 내용을 단순 요약하지 말고, 반드시 ‘사용자의 얼굴형·톤’과 연결해 조언하세요.

────────────────────────
[얼굴형 고정 멘트 – 수정 금지]

땅콩형
광대뼈가 매력적으로 도드라지고 턱선이 날렵한 얼굴형입니다. 얼굴의 굴곡을 부드럽게 연결해 세련된 인상을 줄 수 있어요.
쉐딩: 옆 광대의 돌출된 부분과 턱 끝 라인을 감싸 전체적인 얼굴 라인을 매끄럽게 연결
하이라이터: 눈 밑 앞볼 부위(삼각형 존)와 턱 끝에 사용하여 시선을 얼굴 중앙으로 모아줌
블러셔: 광대 감싸듯 연결

긴형
성숙하고 우아한 이미지를 가진 얼굴형입니다. 시선을 가로로 확장시켜 생기와 볼륨을 더해주는 방식이 잘 어울려요.
쉐딩: 턱 끝 아래
하이라이터: 눈 밑을 터치하여 얼굴의 중안부를 환하게 밝혀줌 
블러셔: 가로 방향(수평)으로 넓게 펴 발라주어 여백을 채워줌

각진형
하관과 턱선이 뚜렷해 고급스럽고 모던한 분위기를 주는 얼굴형입니다. 직선적인 느낌을 중화시키면 부드러운 인상이 살아나요.
쉐딩: 턱 양 끝, 헤어라인 옆쪽 등 윤곽이 뚜렷한 부위에 음영을 줌
하이라이터: 콧대, 턱 중앙 등 얼굴 안쪽에 포인트를 주어 입체감을 살림 
블러셔: 사선 또는 앞볼에 동그랗게 연출

계란형(oval)
전체적인 비율이 균형 잡혀 있어 다양한 스타일을 소화하기 좋은 얼굴형입니다. 인위적인 터치보다는 윤곽을 자연스럽게 살리는 게 좋아요.
쉐딩: 외곽 정돈
하이라이터: 콧대, 턱 끝, C존(광대)
블러셔: 광대 따라 자연스럽게

둥근형
부드러운 곡선 덕분에 어려 보이고 친근한 인상을 주는 얼굴형입니다. 윤곽을 또렷하게 잡아주면 훨씬 세련된 분위기가 살아나요.
쉐딩: 얼굴 양옆 외곽~턱선
하이라이터: 이마, 콧대, 턱 세로 강조
블러셔: 사선 방향으로 연출하여 둥근 볼의 매력은 살리면서도 시원한 느낌을 줌 

하트형(heart)
이마가 시원하고 턱선이 갸름해 러블리한 느낌을 주는 얼굴형입니다. 상안부와 하안부의 밸런스를 맞추는 메이크업이 잘 어울려요.
쉐딩: 관자, 턱 끝
하이라이터: 이마 중앙, 턱 중앙, 눈 밑
블러셔: 볼 중앙 위주로 발라주면 갸름한 턱선과 대비되어 화사한 느낌을 줌 

────────────────────────

[출력 형식 – 반드시 이 형식으로만 출력할 것]

문단 합치기, 한 줄 출력, 자유 서술은 허용하지 않습니다.

[얼굴형]
(얼굴형 고정 멘트 그대로)

[쉐딩]
(쉐딩 조언 1문장)

[하이라이터]
(하이라이터 조언 1문장)

[블러셔]
(블러셔 조언 1문장)

[색조 포인트]
(퍼스널컬러 기준 + Top-N 영상 스타일을 모두 조합한 색조 조언 3문장)

**주의:** 각 항목은 반드시 줄을 바꿔서 한 항목당 한 줄로 출력해야 하며,  
각 항목 앞에는 반드시 '\n' 줄바꿈 문자를 포함하여 출력하세요.
"""

    user_input_data = f"""
[사용자 프로필]
- 얼굴형: {user_face_shape} (예: 둥근형, 긴형, 각진형...)
- 퍼스널컬러: {user_tone} (예: 봄웜, 여쿨, 겨울쿨...)

[원한 상황]
- TPO: {user_tpo} (예: 데이트, 출근...)
- 분위기: {user_mood} (예: 러블리, 시크...)

[추천 영상]
- 제목: {video_title}
- 키워드: {video_keywords}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            temperature=0.7,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_input_data}
            ]
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print("LLM ERROR:", e)
        return f"오늘 같은 {user_tpo} 날에는 {user_mood} 분위기가 딱이에요! {user_tone} 톤에 맞춰 립 컬러만 살짝 조절해 보세요."

# ==========================================
# 6. 결과 페이지
# ==========================================
@app.route("/result", methods=["POST"])
def result():

    tone      = request.form["tone"]
    occasion  = request.form["occasion"]
    tab_mode  = request.form.get("tab_mode", "A")     # A = Mood, B = Star
    mood      = request.form.get("moods", "")
    style_tag = request.form.get("style_tag", "")

    MOOD_DISPLAY = {
        "group_natural": "내추럴 / 청순",
        "group_lovely": "러블리",
        "group_glam": "글램 / 고급",
        "group_chic": "시크 / 스모키 / 고혹",
        "group_hip": "힙·트렌디 / 유니크"
    }

    # mood display name
    mood_display = MOOD_DISPLAY.get(mood, "")

    # 🔥 톤 제외 버튼 여부 체크
    ignore_tone_flag = request.form.get("ignore_tone") == "true"

    # ===============================
    # 1) Tone Key 매핑
    # ===============================
    TONE_MAP = {
        "봄웜": "spring",
        "여쿨": "summer",
        "가을웜": "autumn",
        "겨쿨": "winter",

        "웜톤": "spring",  # 퀴즈에서 선택한 경우
        "쿨톤": "summer",

        "뉴트럴": "neutral",
        "neutral": "neutral"
    }

    tone_key = TONE_MAP.get(tone, "neutral")

    # 🔥 ignore_tone이면 무조건 neutral
    if ignore_tone_flag:
        tone_key = "neutral"

    # ===============================
    # 2) Face Shape Key 매핑
    # ===============================
    face_map = {
        "계란형": "oval",
        "oval": "oval",

        "둥근형": "round",
        "round": "round",

        "땅콩형": "diamond",
        "diamond": "diamond",

        "각진형": "square",
        "square": "square",

        "하트형": "heart",
        "heart": "heart",

        "긴형": "long",
        "long": "long"
    }

    face_key = face_map.get(request.form.get("face_shape", ""), "oval")

    # ===============================
    # 3) 최종 파일 이름 만들기
    # ===============================
    contour_filename = f"{face_key}_{tone_key}.jpeg"
    # --- 이전 단계에서 모은 태그들 (TPO + mood subtags + wannabe 모두 포함) ---
    tags_raw = request.form.get("tags", "")
    prev_tags = [t for t in tags_raw.split(",") if t]

    # --- 제약조건 태그 ---
    cons_raw = request.form.get("constraints", "")
    cons_tags = [t for t in cons_raw.split(",") if t]

    # --- 최종 태그: TPO + mood subtags + wannabe + constraints 전부 병합 ---
    final_tags = prev_tags + cons_tags

    # --- mood-group 정리 ---
    if tab_mode == "B":     # 워너비 선택 → mood 사용 안 함
        user_mood_group = []
    else:
        user_mood_group = mood   # 문자열 1개 (예: "러블리")

    recommendation_data = engine.recommend(
        user_tone=tone,
        user_occasion_group=occasion,
        user_mood_group=user_mood_group,
        selected_tags=final_tags,
        ignore_tone=ignore_tone_flag,
        top_k=5
    )

    # --- 꾸러미 풀기 (결과 리스트 + 알림 메시지 분리) ---
    results = recommendation_data["results"]
    flag_info = recommendation_data["flag_info"]

    # ✅ LLM 스타일 카드 생성 (1등 영상 기준)
    style_tip = ""
    if results:
        top_video = results[0]

        style_tip = generate_llm_style_tip(
            user_face_shape=request.form.get("face_shape"),
            user_tone=tone,
            user_tpo=occasion,
            user_mood=mood_display,
            video_title=top_video["title"],
            video_keywords=top_video.get("moods", "")
        )

    return render_template(
        "results.html",
        results=results,
        flag_info=flag_info,  # 🔥 [핵심] 템플릿에 알림 정보도 같이 던져줌!
        tone=tone,
        face_shape=request.form.get("face_shape", ""),
        occasion=occasion,
        moods=mood,
        mood_display=mood_display,
        tags=final_tags,
        tab_mode=tab_mode,
        contour_filename=contour_filename,
        style_tag=request.form.get("style_tag"),
        nickname=request.form.get("nickname", ""),
        ignore_tone=ignore_tone_flag,
        style_tip=style_tip
    )

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )




