import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from datetime import datetime
import re


# =============================================================================
# 1. [Hard Rule] 동명이인 방지용 ID 리스트
# =============================================================================
WINTER_IDS = [
    50, 184, 210, 225, 234, 574, 663, 678, 892, 1135,
    1172, 1871, 1917, 2228, 2904, 3026, 3036, 3042, 3175,
    3202, 3254, 4599
]

# [NEW] 통계적 계층 필터링을 위한 그룹 상수 정의
COOL_GROUP = ["여쿨", "겨쿨", "쿨톤"]
WARM_GROUP = ["봄웜", "가을웜", "웜톤"]

# =============================================================================
# 2. [Mapping] 매핑 테이블 (하이브리드 구조 완벽 반영)
# =============================================================================
# [NEW] (0) 5가지 대분류 무드 -> DB 라벨 매핑 (UI와 DB의 연결고리)
BROAD_MOOD_MAPPER = {
    "group_natural": ["내추럴(자연스러운)", "청순"],
    "group_lovely": ["러블리"],
    "group_glam": ["글램(글로우)", "고급스러운"],
    "group_chic": ["시크", "스모키", "고혹적"],
    "group_hip": ["힙·트렌디", "유니크"]
}

# (1) 상황(TPO) 상세 태그
TPO_TAG_MAPPER = {
    "#직장인/출근": {
        "type": "hybrid",
        "labels": ["출근/등교"],
        "text": ["직장인", "출근", "오피스", "회사"]
    },
    "#학생/등교": {
        "type": "hybrid",
        "labels": ["출근/등교"],
        "text": ["학생", "학교", "등교", "개강", "교복", "10대", "새내기"]
    },
    "#벚꽃/피크닉": {
        "type": "hybrid",
        "labels": ["데이트"],
        "text": ["벚꽃", "한강", "나들이", "꽃놀이", "피크닉", "소풍", "봄 소풍", "봄 메이크업"]
    },
    "#하객/결혼식": {
        "type": "hybrid",
        "labels": ["격식있는"],
        "text": ["하객", "하객룩"]
    },
    "#증명사진/졸사": {
        "type": "hybrid",
        "labels": ["격식있는"],
        "text": ["증명사진", "여권", "졸업사진", "민증", "면허", "증사"]
    },
    "#연말/크리스마스": {
        "type": "hybrid",
        "labels": ["파티"],
        "text": ["연말", "크리스마스", "성탄절", "홀리데이"]
    }
}

# (2) 분위기(Mood) 상세 태그 (그룹 A~E)
MOOD_TAG_MAPPER = {
    "#꾸안꾸": {"type": "label", "labels": ["내추럴(자연스러운)"]},
    "#민낯/클린걸": {
        "type": "hybrid",
        "labels": ["내추럴(자연스러운)", "청순"],
        "text": ["파데프리", "노파데", "민낯", "쌩얼", "클린걸", "clean girl"]
    },
    "#울먹/청초": {
        "type": "hybrid",
        "labels": ["내추럴(자연스러운)", "청순"],
        "text": ["울먹", "청초", "여리"]
    },
    "#청순": {"type": "label", "labels": ["청순"]},

    "#과즙상": {"type": "label", "labels": ["러블리"]},
    "#복숭아": {
        "type": "hybrid",
        "labels": ["러블리"],
        "text": ["복숭아", "코랄", "피치"]
    },
    "#토끼혀/뽀용": {
        "type": "hybrid",
        "labels": ["러블리"],
        "text": ["토끼혀", "탕후루", "딸기", "뽀용"]
    },

    "#속광/글로우": {"type": "label", "labels": ["글램(글로우)"]},
    "#탕후루/물광": {
        "type": "hybrid",
        "labels": ["글램(글로우)"],
        "text": ["탕후루", "물광", "꿀광", "유리알"]
    },
    "#올드머니/고급": {"type": "label", "labels": ["고급스러운"]},
    "#뮤트/음영": {
        "type": "hybrid",
        "labels": ["글램(글로우)", "고급스러운"],
        "text": ["뮤트", "음영", "가을", "분위기"]
    },

    "#시크/고양이상": {"type": "label", "labels": ["시크"]},
    "#스모키": {"type": "label", "labels": ["스모키"]},
    "#레드립/섹시": {"type": "label", "labels": ["고혹적"]},
    "#도우인": {"type": "text", "text": ["도우인"]},

    "#힙·트렌디": {"type": "label", "labels": ["힙·트렌디"]},
    "#Y2K": {"type": "text", "text": ["y2k"]},
    "#키치/유니크": {"type": "label", "labels": ["유니크"]}
}

# (3) 워너비 스타 (Person)
STYLE_TAG_MAPPER = {
    '#에스파': {
        'include': ['에스파', 'aespa', '카리나', '닝닝', '지젤'],
        'specific_ids': WINTER_IDS
    },
    '#뉴진스': {
        'include': ['뉴진스', 'newjeans', '민지', '하니', '해린', '다니엘', '혜인']
    },
    '#장원영': {'include': ['장원영', '워녕', 'jangwonyoung']},
    '#제니': {'include': ['제니', 'jennie']},
    '#로제': {'include': ['로제', 'rosé']},
    '#아이돌커버': {'include': ['아이돌', 'idol', '걸그룹', 'kpop', '커버']},
    '#배우메이크업': {'include': ['배우', '여배우', '드라마', '여주', '수지']}
}

# (4) 제약조건 (Constraints)
CONSTRAINT_MAPPER = {
    '#노아이라인': {
        'include': [
            r"노\s*아이라인",
            r"no\s*아이라인",
            r"아이라인\s*[x✖️✕❌🚫]"
        ]
    },
    '#노파데': {
        'include': [
            r"파데\s*프리",
            r"파데\s*free",
            r"노\s*파데",
            r"no\s*파데",
            r"파데\s*[x✖️✕❌🚫]",
            r"파데\s*(없는|없이)",
            r"파데프리[^\w]?",
            r"파운데이션\s*프리",
            r"foundation[-\s]*free",
            r"no\s*foundation"
        ]
    },
    '#무쌍': {'include': [r"무\s*쌍"]},
    '#속쌍': {'include': [r"속\s*쌍", r"속쌍꺼풀"]},
    '#애교살': {'include': [r"애교\s*살", r"애굣살"]},
    '#오버립': {'include': [r"오버\s*립"]}
}


# =============================================================================
# 3. 추천 엔진 클래스
# =============================================================================
class MakeupRecommender:

    def __init__(self, use_csv_for_test=False, csv_path=None):
        self.df = pd.DataFrame()

        if use_csv_for_test and csv_path:
            print(f"📂 [Test Mode] CSV 로드: {csv_path}")
            self.df = pd.read_csv(csv_path)
        else:
            self.db_url = 'mysql+pymysql://root:0000@localhost:3306/makeup_recommender'
            self.engine = create_engine(self.db_url)
            print("⏳ [Prod Mode] DB 데이터 로드 중...")
            try:
                self.df = pd.read_sql('SELECT * FROM videos', con=self.engine)
            except Exception as e:
                print(f"❌ DB 로드 실패: {e}")
                return

        if not self.df.empty:
            self._preprocess_data()
            print(f"✅ 추천 엔진 준비 완료! (총 {len(self.df)}개 영상)")

    # -----------------------------
    # 🔥 (1) 정상 함수 정의
    # -----------------------------
    def normalize_text(self, s):
        if pd.isna(s):
            return ""
        s = str(s).lower()
        s = re.sub(r"[^\w가-힣ㄱ-ㅎㅏ-ㅣ\s]", " ", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    # -----------------------------
    # 🔥 (2) preprocess에서 full_text 생성
    # -----------------------------
    def _preprocess_data(self):
        self.df['moods'] = self.df['moods'].fillna('')
        self.df['occasions'] = self.df['occasions'].fillna('')
        self.df['title'] = self.df['title'].fillna('')
        self.df['description_keywords'] = self.df['description_keywords'].fillna('')

        self.df['moods_list'] = self.df['moods'].str.split(',').apply(lambda x: [i.strip() for i in x])
        self.df['occasions_list'] = self.df['occasions'].str.split(',').apply(lambda x: [i.strip() for i in x])

        self.df['full_text'] = (
            self.df['title'] + " " +
            self.df['description_keywords'] + " "
        ).apply(self.normalize_text)

        # [MODIFIED] 페널티 로직 제거 -> 단순 가산점 방식으로 변경
    def _calculate_tone_score(self, user_tone, video_tone, ignore_tone=False):
        if ignore_tone:
            return 0
        if not video_tone or video_tone == "미분류":
            return 0

        # NOTE: 이미 필터링이 된 상태로 들어오므로, 여기 있는 video_tone은 모두 user_tone과 '같은 계열'임.

        # 1. Exact Match (완벽 일치)
        if user_tone == video_tone:
            return 100

        # 2. Group Match (계열만 일치) -> 필터링 통과했으면 무조건 여기 해당
        return 40  # 적당한 기본 점수 부여

    def _calculate_quality_score(self, row):
        try:
            pub_date = pd.to_datetime(row['published_at']) if isinstance(row['published_at'], str) else row['published_at']
            days_diff = (datetime.now() - pub_date).days
            recency = 1 / (1 + days_diff / 730)
        except:
            recency = 0

        views = np.log1p(row['views']) if 'views' in row else 0
        likes = np.log1p(row['likes']) if 'likes' in row else 0

        return ((views * 0.3 + likes * 0.7) / 15.0 * 0.7 + recency * 0.3) * 10

    def _apply_constraints(self, row, constraints_data):
        score_adjustment = 0
        full_text = row['full_text']

        # 1. Specific IDs (동명이인 등)
        if 'video_id' in row and row['video_id'] in constraints_data['specific_ids']:
            score_adjustment += 100

        # 2. Pattern Groups (태그별 그룹 채점)
        # 태그 하나당(pattern_group 하나당) 딱 한 번만 1500점을 줌
        for patterns in constraints_data['pattern_groups']:
            matched = False
            for pattern in patterns:
                if re.search(pattern, full_text, re.IGNORECASE):
                    matched = True
                    break  # 유의어 하나 찾았으면, 나머지 유의어는 볼 필요 없음 (Break)

            if matched:
                score_adjustment += 1500  # 태그 1개 만족 시 1500점 (중복 X)

        return score_adjustment

    def _filter_hybrid(self, df, mapper_data):
        m_type = mapper_data.get('type')

        if m_type == 'label':
            labels = mapper_data['labels']
            pat = '|'.join(map(re.escape, labels))
            return df[
                df['moods'].str.contains(pat, case=False, na=False) |
                df['occasions'].str.contains(pat, case=False, na=False)
            ]

        elif m_type == 'text':
            keywords = mapper_data['text']
            pat = '|'.join(map(re.escape, keywords))
            return df[df['full_text'].str.contains(pat, case=False, na=False)]

        elif m_type == 'hybrid':
            labels = mapper_data['labels']
            text_kw = mapper_data['text']

            label_pat = '|'.join(map(re.escape, labels))
            text_pat = '|'.join(map(re.escape, text_kw))

            label_mask = (
                df['moods'].str.contains(label_pat, case=False, na=False) |
                df['occasions'].str.contains(label_pat, case=False, na=False)
            )
            text_mask = df['full_text'].str.contains(text_pat, case=False, na=False)

            return df[label_mask & text_mask]

        return df

    # -------------------------------------------------------------------------
    # 추천 함수 시작
    # -------------------------------------------------------------------------

    def _calculate_score_internal(self, row, target_occasions, target_moods, user_tone, ignore_tone, constraints_data):
        # 1. TPO 점수
        matched_occ = set(target_occasions) & set(row['occasions_list'])
        s_occ = (len(matched_occ) / len(target_occasions) * 100) if target_occasions else 0

        # 2. Mood 점수
        if not target_moods:
            s_mood = 0
        else:
            matched_count = sum(1 for tm in target_moods if any(tm in rm for rm in row['moods_list']))
            s_mood = (matched_count / len(target_moods)) * 100

        # 3. Tone 점수
        s_tone = self._calculate_tone_score(user_tone, row['tone'], ignore_tone=ignore_tone)

        # 4. Quality & Constraints
        s_qual = self._calculate_quality_score(row)
        s_constr = self._apply_constraints(row, constraints_data)

        return (s_occ * 0.4) + (s_mood * 0.35) + (s_tone * 0.25) + s_qual + s_constr

    def recommend(self, user_tone, user_occasion_group, user_mood_group, selected_tags=None, ignore_tone=False,
                      top_k=5):
        if selected_tags is None:
            selected_tags = []

        # ---------------------------------------------------------
        # 0. 톤 필터링 (기본 베이스 - 기존과 동일)
        # ---------------------------------------------------------
        df_base = self.df.copy()
        if not ignore_tone and user_tone:
            target_group = []
            if any(c in user_tone for c in COOL_GROUP):
                target_group = COOL_GROUP
            elif any(w in user_tone for w in WARM_GROUP):
                target_group = WARM_GROUP

            if target_group:
                df_base = df_base[df_base['tone'].apply(lambda x: any(t in str(x) for t in target_group))]

        # ---------------------------------------------------------
        # 1. 태그 분류 (스타일 / 무드 / TPO)
        # ---------------------------------------------------------
        # (1) 스타일 태그 확인 (Track 결정용)
        style_tag_selected = next((tag for tag in selected_tags if tag in STYLE_TAG_MAPPER), None)

        # (2) Mood 상세 태그
        mood_sub_tags = [tag for tag in selected_tags if tag in MOOD_TAG_MAPPER]

        # (3) TPO 상세 태그 & 그룹
        tpo_labels = []
        if isinstance(user_occasion_group, str):
            tpo_labels.append(user_occasion_group)
        elif isinstance(user_occasion_group, list):
            tpo_labels.extend(user_occasion_group)

        for tag in selected_tags:
            if tag in TPO_TAG_MAPPER:
                tpo_labels.extend(TPO_TAG_MAPPER[tag].get('labels', []))
        tpo_labels = list(set(tpo_labels))

        # (4) Mood 그룹 (대분류)
        mood_broad_labels = []
        if isinstance(user_mood_group, str):
            if user_mood_group in BROAD_MOOD_MAPPER:
                mood_broad_labels = BROAD_MOOD_MAPPER[user_mood_group]
            else:
                mood_broad_labels = [user_mood_group]

        # (5) 제약조건 데이터 준비 (점수 계산용)
        constraint_pattern_groups = []
        specific_ids = []
        for tag in selected_tags:
            if tag in CONSTRAINT_MAPPER:
                patterns = CONSTRAINT_MAPPER[tag].get('include', [])
                if patterns:
                    constraint_pattern_groups.append(patterns)
            if tag in STYLE_TAG_MAPPER:
                if 'specific_ids' in STYLE_TAG_MAPPER[tag]:
                    specific_ids.extend(STYLE_TAG_MAPPER[tag]['specific_ids'])
                if 'include' in STYLE_TAG_MAPPER[tag]:
                    constraint_pattern_groups.append(STYLE_TAG_MAPPER[tag]['include'])

        final_constraints_data = {'pattern_groups': constraint_pattern_groups, 'specific_ids': specific_ids}

        # [Helper] 결과 계산 함수
        def fetch_results(candidate_df):
            if candidate_df.empty:
                return []
            candidate_df = candidate_df.copy()
            candidate_df['score'] = candidate_df.apply(
                lambda row: self._calculate_score_internal(
                    row, tpo_labels, mood_broad_labels, user_tone, ignore_tone, final_constraints_data
                ), axis=1
            )
            return candidate_df.sort_values('score', ascending=False).head(top_k)[
                ['video_id', 'title', 'channel', 'url', 'score', 'tone', 'moods', 'occasions']
            ].to_dict(orient='records')

        # =========================================================
        # 3. 이원화 트랙 & Fallback 로직 실행
        # =========================================================
        final_results = []
        flag_info = {"status": "success", "msg": ""}

        # 🚦 Track 2: 워너비 스타 우선 (Star > TPO)
        if style_tag_selected:
            mapper = STYLE_TAG_MAPPER[style_tag_selected]
            star_mask = pd.Series([False] * len(df_base), index=df_base.index)
            if 'include' in mapper:
                pat = '|'.join(map(re.escape, mapper['include']))
                star_mask |= df_base['full_text'].str.contains(pat, case=False, na=False)
            if 'specific_ids' in mapper:
                star_mask |= df_base['video_id'].isin(mapper['specific_ids'])

            df_star = df_base[star_mask]

            # [Step 1] 스타 + TPO
            if tpo_labels:
                pat_tpo = '|'.join(map(re.escape, tpo_labels))
                df_step1 = df_star[df_star['occasions'].str.contains(pat_tpo, case=False, na=False)]
                final_results = fetch_results(df_step1)

                if final_results:
                    flag_info["msg"] = "선택하신 스타일과 상황을 모두 반영한 결과예요."

                else:
                    # [Step 2] TPO 포기
                    final_results = fetch_results(df_star)
                    flag_info["status"] = "tpo_dropped"
                    flag_info["msg"] = f"'{style_tag_selected}' 스타일의 상황별 영상은 부족해서, 분위기가 가장 잘 맞는 추천을 가져왔어요."

            else:
                final_results = fetch_results(df_star)

        # 🚦 Track 1: 일반 무드 우선 (TPO > Mood)
        else:
            # ---------------------------------------------------
            # 🔥 [수정] TPO 필터링 강화 (대분류 + 상세 태그 둘 다 검사)
            # ---------------------------------------------------
            df_tpo = df_base.copy()

            # 1) 상황 대분류 (예: "격식있는") 필터링
            if isinstance(user_occasion_group, str) and user_occasion_group:
                df_tpo = df_tpo[df_tpo['occasions'].str.contains(re.escape(user_occasion_group), case=False, na=False)]

            # 2) 상황 상세 태그 (예: "#하객/결혼식") '하드 필터링' 적용
            # 👉 이게 추가되어야 "하객" 글자가 없는 영상이 싹 사라집니다!
            for tag in selected_tags:
                if tag in TPO_TAG_MAPPER:
                    mapper = TPO_TAG_MAPPER[tag]
                    df_tpo = self._filter_hybrid(df_tpo, mapper)

            # [Step 1] Mood 상세 태그 시도 (예: #도우인)
            if mood_sub_tags:
                current_mood_tag = mood_sub_tags[0]
                mapper = MOOD_TAG_MAPPER[current_mood_tag]
                df_step1 = self._filter_hybrid(df_tpo, mapper)
                final_results = fetch_results(df_step1)

                if final_results:
                    flag_info["msg"] = "선택하신 상황과 무드를 모두 고려한 추천이에요."
                else:
                    # [Step 2] 상세 태그 포기 (#도우인 탈락) -> 대분류(시크) 시도
                    # ⚠️ 중요: df_tpo는 이미 '하객'만 남은 상태이므로, 여기서 '시크'를 찾으면 '하객+시크'가 됨
                    if mood_broad_labels:
                        pat_broad = '|'.join(map(re.escape, mood_broad_labels))
                        df_step2 = df_tpo[df_tpo['moods'].str.contains(pat_broad, case=False, na=False)]
                        final_results = fetch_results(df_step2)

                        if final_results:
                            flag_info["status"] = "mood_detail_dropped"
                            flag_info["msg"] = f"'{current_mood_tag}' 느낌과 완전히 일치하는 영상은 없었지만, 가장 비슷한 분위기의 추천을 준비했어요."

                        else:
                            # [Step 3] Mood 완전 포기 (시크 탈락) -> TPO(하객)만 봄
                            final_results = fetch_results(df_tpo)
                            flag_info["status"] = "mood_all_dropped"
                            flag_info["msg"] = f"선택하신 분위기와 정확히 일치하지는 않지만, '{tpo_labels[0] if tpo_labels else ''}' 상황에 가장 잘 어울리는 추천이에요."

                    else:
                        final_results = fetch_results(df_tpo)
                        flag_info["status"] = "mood_all_dropped"
                        flag_info["msg"] = "선택하신 분위기와는 다를 수 있지만, 상황에 맞는 스타일 중심으로 추천했어요."

            else:
                # 상세 태그 없으면 대분류로 바로 시작
                if mood_broad_labels:
                    pat_broad = '|'.join(map(re.escape, mood_broad_labels))
                    df_step1 = df_tpo[df_tpo['moods'].str.contains(pat_broad, case=False, na=False)]
                    final_results = fetch_results(df_step1)

                    if not final_results:
                        final_results = fetch_results(df_tpo)
                        flag_info["status"] = "mood_broad_dropped"
                        flag_info["msg"] = f"조건에 완전히 맞는 영상은 없었지만, 가장 자연스럽게 어울릴 수 있는 '{tpo_labels[0] if tpo_labels else ''}' 스타일을 기준으로 추천했어요."

                else:
                    final_results = fetch_results(df_tpo)

        return {"results": final_results, "flag_info": flag_info}



    # =========================================================================
    # 제약조건 매칭 함수
    # =========================================================================
    def _tag_match(self, df, tag):
        rule = CONSTRAINT_MAPPER.get(tag, {})

        mask = pd.Series([True] * len(df), index=df.index)

        if "include" in rule:
            inc_mask = pd.Series([False] * len(df), index=df.index)
            for kw in rule["include"]:
                cond = df["full_text"].str.contains(kw, case=False, na=False)
                inc_mask |= cond
            mask &= inc_mask

        return mask

    # =========================================================================
    # 제약조건 필터링 - available tags
    # =========================================================================
    def get_available_tags(self, user_occasion_group=None, user_mood_group=None,
                           style_tag=None, user_tone=None, selected_pre_tags=None):

        if selected_pre_tags is None:
            selected_pre_tags = []

        df = self.df.copy()

        # ---------------------------------------------------------
        # 1. 톤 필터링 (입구컷) - 기존과 동일
        # ---------------------------------------------------------
        if user_tone:
            target_group = []
            if any(c in user_tone for c in COOL_GROUP):
                target_group = COOL_GROUP
            elif any(w in user_tone for w in WARM_GROUP):
                target_group = WARM_GROUP

            if target_group:
                df = df[df['tone'].apply(lambda x: any(t in str(x) for t in target_group))]

        # ---------------------------------------------------------
        # 2. [NEW & CRITICAL] 세부 태그 필터링 (recommend 로직 이식)
        # ---------------------------------------------------------
        # 세부 태그가 선택되었다면, 대분류보다 우선해서 데이터를 좁혀야 함 (교집합 문제 해결)

        mood_tag_selected = False

        for tag in selected_pre_tags:
            # 1. Mood 관련 세부 태그가 있으면 강하게 필터링 (Hard Filter)
            if tag in MOOD_TAG_MAPPER:
                df = self._filter_hybrid(df, MOOD_TAG_MAPPER[tag])
                mood_tag_selected = True

            # 2. ⭐ [핵심 수정 부분] TPO 관련 세부 태그도 강하게 필터링 (Hard Filter)
            elif tag in TPO_TAG_MAPPER:
                df = self._filter_hybrid(df, TPO_TAG_MAPPER[tag])  # 👈 이 필터링이 추가되어야 합니다.
                tpo_tag_selected = True

            # TPO 관련 세부 태그 처리 (필요시 활성화, 여기선 필터링보단 TPO 그룹이 처리함)
            # 하지만 TPO 상세 태그로 확실히 좁히고 싶다면 아래 주석 해제
            # elif tag in TPO_TAG_MAPPER:
            #     df = self._filter_hybrid(df, TPO_TAG_MAPPER[tag])

        # ---------------------------------------------------------
        # 3. 대분류 필터링 (세부 태그가 없을 때만 작동)
        # ---------------------------------------------------------

        # Occasion (TPO) - 기존 로직 유지
        if user_occasion_group:
            pat = re.escape(user_occasion_group)
            df = df[df["occasions"].str.contains(pat, case=False, na=False)]

        # Mood (대분류) - [수정됨] 세부 태그(mood_tag_selected)가 없을 때만 대분류로 넓게 봄
        if not mood_tag_selected and user_mood_group:
            if user_mood_group in BROAD_MOOD_MAPPER:
                target_labels = BROAD_MOOD_MAPPER[user_mood_group]
                if target_labels:
                    df = df[df["moods_list"].apply(
                        lambda lst: any(tl in lst for tl in target_labels)
                    )]

        # ---------------------------------------------------------
        # 4. 스타일 태그 (워너비) - 기존 로직 유지
        # ---------------------------------------------------------
        if style_tag and style_tag in STYLE_TAG_MAPPER:
            inc = STYLE_TAG_MAPPER[style_tag].get("include", [])
            if inc:
                pat = "|".join(inc)
                df = df[df["full_text"].str.contains(pat, case=False, na=False)]

        # ---------------------------------------------------------
        # 5. 최종 가용 태그 계산 (Constraint 매칭)
        # ---------------------------------------------------------
        available = []
        for tag in CONSTRAINT_MAPPER.keys():
            mask = self._tag_match(df, tag)
            cnt = int(mask.sum())
            if cnt > 0:
                available.append(tag)

        return available


    # =========================================================================
    # compatible tags 계산
    # =========================================================================
    # =========================================================================
    # compatible tags 계산 (최종 수정본)
    # =========================================================================
    def get_compatible_tags(self, selected_tags,
                            user_occasion_group=None,
                            user_mood_group=None,
                            style_tag=None,
                            user_tone=None,
                            selected_pre_tags=None):

        if selected_pre_tags is None:
            selected_pre_tags = []

        df_base = self.df.copy()

        # 1. 톤 필터링 (입구 컷)
        if user_tone:
            target_group = []
            if any(c in user_tone for c in COOL_GROUP):
                target_group = COOL_GROUP
            elif any(w in user_tone for w in WARM_GROUP):
                target_group = WARM_GROUP

            if target_group:
                df_base = df_base[df_base['tone'].apply(lambda x: any(t in str(x) for t in target_group))]

            # 🔥 [수정 1] TPO 상세 태그 필터링 추가 (누락되었던 부분)
            mood_tag_selected = False
            for tag in selected_pre_tags:
                if tag in MOOD_TAG_MAPPER:
                    df_base = self._filter_hybrid(df_base, MOOD_TAG_MAPPER[tag])
                    mood_tag_selected = True
                elif tag in TPO_TAG_MAPPER:  # 👈 여기가 추가되어야 상황 착각을 안 합니다!
                    df_base = self._filter_hybrid(df_base, TPO_TAG_MAPPER[tag])

        # 2. 대분류 필터링 (Occasion)
        if user_occasion_group:
            pat = re.escape(user_occasion_group)
            df_base = df_base[df_base["occasions"].str.contains(pat, case=False, na=False)]

        # 3. 대분류 필터링 (Mood)
        if not mood_tag_selected and user_mood_group:
            if user_mood_group in BROAD_MOOD_MAPPER:
                moods = BROAD_MOOD_MAPPER[user_mood_group]
                df_base = df_base[df_base["moods_list"].apply(
                    lambda lst: any(m in lst for m in moods)
                )]

        # 4. 스타일 태그 필터링
        if style_tag:
            inc = STYLE_TAG_MAPPER[style_tag].get("include", [])
            if inc:
                pat = "|".join(inc)
                df_base = df_base[df_base["full_text"].str.contains(pat, case=False, na=False)]
        else:
            if user_mood_group:
                if user_mood_group in BROAD_MOOD_MAPPER:
                    moods = BROAD_MOOD_MAPPER[user_mood_group]
                else:
                    moods = [user_mood_group]

                df_base = df_base[df_base["moods_list"].apply(
                    lambda lst: any(m in lst for m in moods)
                )]

        if not selected_tags:
            return list(CONSTRAINT_MAPPER.keys())

        df_selected = df_base.copy()

        selected_constraint_tags = [
            t for t in selected_tags if t in CONSTRAINT_MAPPER
        ]

        # 5. 제약조건 교집합 검사
        for tag in selected_constraint_tags:
            mask = self._tag_match(df_selected, tag)
            df_selected = df_selected[mask]

            # 🔥 [수정 2] 결과가 0개면 빈 리스트 반환 (거짓말 금지)
            if df_selected.empty:
                return []  # 👈 selected_tags 대신 []를 반환해야 버튼이 꺼집니다!

        compatible = set(selected_tags)

        for tag in CONSTRAINT_MAPPER.keys():
            mask = self._tag_match(df_selected, tag)
            if mask.any():
                compatible.add(tag)

        return list(compatible)
