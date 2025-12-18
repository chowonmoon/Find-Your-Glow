# ✨ Find Your Glow (AI Makeup Recommender)

> **"사용자의 얼굴형, 톤, TPO에 맞춰 유튜브 튜토리얼과 메이크업 팁을 추천해주는 초개인화 뷰티 가이드"**

<br>

## 🔗 Project Links
- **Live Demo:** http://chowon.pythonanywhere.com
- **Presentation:** https://github.com/hwangaejin0-lgtm/Find-Your-Glow/blob/main/Presentation.pdf
<br>

## 💡 Project Background
기존 뷰티 플랫폼은 '제품 판매'나 단순 '가상 체험'에 그쳐, 소비자가 원하는 **"이 분위기 어떻게 내요?"**라는 스타일링 니즈를 충족하지 못했습니다.
**Find Your Glow**는 사용자의 특성(퍼스널컬러, 얼굴형)과 상황(TPO)을 분석하여, 가장 적합한 **유튜브 튜토리얼 영상**과 **맞춤형 메이크업 가이드**를 제공합니다.

<br>

## 🛠️ Tech Stack
| Category | Stack |
| --- | --- |
| **Backend** | Python, Flask |
| **Frontend** | HTML5, CSS3, JavaScript |
| **Data Processing** | Pandas, NumPy |
| **Deployment** | PythonAnywhere |

<br>

## 🌟 Key Features (Core Logic)

### 1. Dual-Track Recommendation System
사용자의 검색 의도를 파악하여 알고리즘을 이원화했습니다.
- **Track A (Situation-First):** 상황(TPO)과 분위기(Mood) 적합도를 최우선으로 추천 (가중치: TPO 40%, Mood 35%).
- **Track B (Star-First):** 워너비 스타(예: 장원영, 에스파) 스타일을 선택 시, 해당 키워드를 우선 매칭.

### 2. Constraint Boosting & Re-ranking
단순 필터링(AND 조건)으로 인해 결과가 '0건'이 되는 문제를 방지하기 위해 **가산점(Boosting)** 방식을 도입했습니다.
- 필수 조건(Tone)은 필터링하되, 희소 조건(#무쌍, #노파데 등)은 **+1500점의 가산점**을 부여하여 해당 영상이 있을 경우 최상단으로 순위를 역전시킵니다.

### 3. Zero-Result Guardrail (UX Engineering)
사용자가 선택 불가능한 옵션을 클릭하여 '결과 없음' 페이지에 도달하는 것을 방지합니다.
- **Dynamic UI Control:** 프론트엔드에서 실시간으로 교집합 데이터를 확인하여, 결과가 없는 조합의 버튼은 자동으로 **비활성화(Disabled)** 처리합니다.

<br>

## 📂 Project Structure
```bash
├── app.py           # Flask Entry Point
├── core.py          # Recommendation Engine & Logic
├── templates/       # HTML Templates (Jinja2)

└── static/          # CSS, Images, Scripts
